from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.main import app
from app.models.catalogs import (
    Object,
    ObjectStage,
    Stage,
)
from app.models.contracts import Contract, ObjectContract
from app.models.reports import ResponsibleObjectAssignment
from app.models.users import User

client = TestClient(app)


async def _seed_snapshot_scenario(suffix: str, *, with_contracts: bool = True):
    """Seed dev-user, an object with stage/assignment and optional contracts."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.max_user_id == "dev-user")
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                max_user_id="dev-user",
                full_name="Dev User",
                role="responsible",
            )
            session.add(user)
            await session.flush()

        obj = Object(
            code=f"obj-{suffix}", name="Объект А", execution_method="own"
        )
        other_obj = Object(
            code=f"obj-other-{suffix}", name="Объект Б", execution_method="own"
        )
        stage = Stage(code=f"stg-{suffix}", name="Этап")
        session.add_all([obj, other_obj, stage])
        await session.flush()

        session.add(ObjectStage(object_id=obj.id, stage_id=stage.id))
        session.add(
            ResponsibleObjectAssignment(
                user_id=user.id,
                object_id=obj.id,
                active_from=date(2026, 1, 1),
                active_to=date(2026, 12, 31),
                schedule_type="daily",
            )
        )

        contract_primary = None
        contract_other = None
        contract_inactive = None
        if with_contracts:
            contract_primary = Contract(
                code=f"ctr-{suffix}", full_name="Договор №1 подробный"
            )
            contract_other = Contract(
                code=f"ctr-foreign-{suffix}", full_name="Чужой договор"
            )
            contract_inactive = Contract(
                code=f"ctr-inactive-{suffix}", full_name="Неактивный договор"
            )
            session.add_all([contract_primary, contract_other, contract_inactive])
            await session.flush()

            # primary active mapping to obj
            session.add(
                ObjectContract(
                    object_id=obj.id,
                    contract_id=contract_primary.id,
                    is_primary=True,
                    active=True,
                )
            )
            # foreign contract mapped to other_obj only
            session.add(
                ObjectContract(
                    object_id=other_obj.id,
                    contract_id=contract_other.id,
                    is_primary=True,
                    active=True,
                )
            )
            # inactive mapping to obj
            session.add(
                ObjectContract(
                    object_id=obj.id,
                    contract_id=contract_inactive.id,
                    is_primary=False,
                    active=False,
                )
            )
        await session.commit()

        return {
            "user": user,
            "obj": obj,
            "other_obj": other_obj,
            "stage": stage,
            "contract_primary": contract_primary,
            "contract_other": contract_other,
            "contract_inactive": contract_inactive,
        }


def _report_payload(**overrides) -> dict:
    payload = {
        "report_date": "2026-07-14",
        "object_id": 1,
        "stage_id": 1,
        "contractor_id": None,
        "staff": {"itr": 1, "internal": 0, "external": 0},
        "soil_export_m3": None,
        "equipment": [],
        "works": [],
        "comment": "Тест",
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_foreign_contract_rejected():
    data = await _seed_snapshot_scenario("o05-foreign")
    payload = _report_payload(
        object_id=data["obj"].id,
        stage_id=data["stage"].id,
        contract_id=data["contract_other"].id,
    )
    response = client.post(
        "/api/reports",
        json=payload,
        headers={"Idempotency-Key": "key-o05-foreign"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_inactive_mapping_rejected():
    data = await _seed_snapshot_scenario("o05-inactive")
    payload = _report_payload(
        object_id=data["obj"].id,
        stage_id=data["stage"].id,
        contract_id=data["contract_inactive"].id,
    )
    response = client.post(
        "/api/reports",
        json=payload,
        headers={"Idempotency-Key": "key-o05-inactive"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_single_primary_contract_auto_filled():
    data = await _seed_snapshot_scenario("o05-auto")
    # no contract_id provided -> backend substitutes the single primary contract
    payload = _report_payload(
        object_id=data["obj"].id,
        stage_id=data["stage"].id,
    )
    response = client.post(
        "/api/reports",
        json=payload,
        headers={"Idempotency-Key": "key-o05-auto"},
    )
    assert response.status_code == 201
    report_id = response.json()["id"]

    detail = client.get(f"/api/reports/{report_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["contract_id"] == data["contract_primary"].id
    assert body["contract_code_snapshot"] == data["contract_primary"].code
    assert (
        body["contract_full_name_snapshot"] == data["contract_primary"].full_name
    )


@pytest.mark.asyncio
async def test_multiple_active_contracts_require_explicit_choice():
    data = await _seed_snapshot_scenario("o05-multiple")
    async with AsyncSessionLocal() as session:
        second = Contract(
            code="ctr-o05-multiple-2",
            full_name="Договор №2 подробный",
        )
        session.add(second)
        await session.flush()
        session.add(
            ObjectContract(
                object_id=data["obj"].id,
                contract_id=second.id,
                is_primary=False,
                active=True,
            )
        )
        await session.commit()

    payload = _report_payload(
        object_id=data["obj"].id,
        stage_id=data["stage"].id,
    )
    response = client.post(
        "/api/reports",
        json=payload,
        headers={"Idempotency-Key": "key-o05-multiple"},
    )
    assert response.status_code == 422
    assert "Выберите договор" in response.json()["detail"]["error"]


@pytest.mark.asyncio
async def test_idempotent_submit_no_duplicate():
    data = await _seed_snapshot_scenario("o05-idem")
    payload = _report_payload(
        object_id=data["obj"].id,
        stage_id=data["stage"].id,
        contract_id=data["contract_primary"].id,
    )
    response1 = client.post(
        "/api/reports",
        json=payload,
        headers={"Idempotency-Key": "key-o05-idem"},
    )
    response2 = client.post(
        "/api/reports",
        json=payload,
        headers={"Idempotency-Key": "key-o05-idem"},
    )
    assert response1.status_code == 201
    assert response2.status_code == 201
    assert response1.json()["id"] == response2.json()["id"]


@pytest.mark.asyncio
async def test_report_snapshots_saved():
    data = await _seed_snapshot_scenario("o05-snap")
    payload = _report_payload(
        object_id=data["obj"].id,
        stage_id=data["stage"].id,
        contract_id=data["contract_primary"].id,
    )
    response = client.post(
        "/api/reports",
        json=payload,
        headers={"Idempotency-Key": "key-o05-snap"},
    )
    assert response.status_code == 201
    report_id = response.json()["id"]

    detail = client.get(f"/api/reports/{report_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["object_name_snapshot"] == data["obj"].name
    assert body["contract_code_snapshot"] == data["contract_primary"].code
    assert (
        body["contract_full_name_snapshot"] == data["contract_primary"].full_name
    )
