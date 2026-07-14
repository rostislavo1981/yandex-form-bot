from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.main import app
from app.models.catalogs import (
    Contractor,
    EquipmentType,
    Object,
    ObjectStage,
    Stage,
    Unit,
    WorkMethod,
    WorkType,
    WorkTypeMethod,
)
from app.models.reports import (
    ResponsibleObjectAssignment,
)
from app.models.users import User

client = TestClient(app)


async def _seed_full_report_scenario(suffix: str):
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

        contractor = Contractor(code=f"ctr-{suffix}", name="Подрядчик")
        unit = Unit(code=f"m3-{suffix}", name="кубометр", symbol="м³")
        unit2 = Unit(code=f"h-{suffix}", name="час", symbol="ч")
        session.add_all([contractor, unit, unit2])
        await session.flush()

        obj_own = Object(
            code=f"obj-own-{suffix}", name="Объект собств", execution_method="own"
        )
        obj_contractor = Object(
            code=f"obj-ctr-{suffix}",
            name="Объект подряд",
            execution_method="contractor",
            default_contractor_id=contractor.id,
        )
        stage = Stage(code=f"stg-{suffix}", name="Этап")
        stage_other = Stage(code=f"stg-other-{suffix}", name="Чужой этап")
        equipment = EquipmentType(
            code=f"eq-{suffix}", name="Экскаватор", default_unit_id=unit.id
        )
        work_type = WorkType(
            code=f"wt-{suffix}", name="Земляные", default_unit_id=unit.id
        )
        method = WorkMethod(code=f"wm-{suffix}", name="Механизированный")
        session.add_all(
            [obj_own, obj_contractor, stage, stage_other, equipment, work_type, method]
        )
        await session.flush()

        session.add_all(
            [
                ObjectStage(object_id=obj_own.id, stage_id=stage.id),
                ObjectStage(object_id=obj_contractor.id, stage_id=stage.id),
            ]
        )
        session.add(
            WorkTypeMethod(work_type_id=work_type.id, work_method_id=method.id)
        )
        await session.flush()

        for obj in [obj_own, obj_contractor]:
            session.add(
                ResponsibleObjectAssignment(
                    user_id=user.id,
                    object_id=obj.id,
                    active_from=date(2026, 1, 1),
                    active_to=date(2026, 12, 31),
                    schedule_type="daily",
                )
            )
        await session.commit()

        return {
            "user": user,
            "contractor": contractor,
            "unit": unit,
            "unit2": unit2,
            "obj_own": obj_own,
            "obj_contractor": obj_contractor,
            "stage": stage,
            "stage_other": stage_other,
            "equipment": equipment,
            "work_type": work_type,
            "method": method,
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
async def test_create_report_happy_path():
    data = await _seed_full_report_scenario("rpt-1")
    payload = _report_payload(
        object_id=data["obj_own"].id,
        stage_id=data["stage"].id,
        equipment=[
            {
                "equipment_type_id": data["equipment"].id,
                "ownership": "own",
                "unit_id": data["unit"].id,
                "quantity": "8.00",
            }
        ],
        works=[
            {
                "work_type_id": data["work_type"].id,
                "work_method_id": data["method"].id,
                "unit_id": data["unit"].id,
                "quantity": "45.00",
            }
        ],
        soil_export_m3="24.00",
    )
    response = client.post(
        "/api/reports",
        json=payload,
        headers={"Idempotency-Key": "key-rpt-1"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"] is not None
    assert body["status"] == "submitted"


@pytest.mark.asyncio
async def test_create_report_contractor_required():
    data = await _seed_full_report_scenario("rpt-2")
    payload = _report_payload(
        object_id=data["obj_contractor"].id,
        stage_id=data["stage"].id,
        contractor_id=None,
        staff={"itr": 1, "internal": 0, "external": 0},
    )
    response = client.post(
        "/api/reports",
        json=payload,
        headers={"Idempotency-Key": "key-rpt-2"},
    )
    assert response.status_code == 422
    assert "contractor" in response.text.lower() or "required" in response.text.lower()


@pytest.mark.asyncio
async def test_create_report_rejects_foreign_stage():
    data = await _seed_full_report_scenario("rpt-3")
    payload = _report_payload(
        object_id=data["obj_own"].id,
        stage_id=data["stage_other"].id,
        staff={"itr": 1, "internal": 0, "external": 0},
    )
    response = client.post(
        "/api/reports",
        json=payload,
        headers={"Idempotency-Key": "key-rpt-3"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_report_idempotent():
    data = await _seed_full_report_scenario("rpt-4")
    payload = _report_payload(
        object_id=data["obj_own"].id,
        stage_id=data["stage"].id,
        staff={"itr": 2, "internal": 0, "external": 0},
    )
    response1 = client.post(
        "/api/reports",
        json=payload,
        headers={"Idempotency-Key": "key-rpt-4"},
    )
    response2 = client.post(
        "/api/reports",
        json=payload,
        headers={"Idempotency-Key": "key-rpt-4"},
    )
    assert response1.status_code == 201
    assert response2.status_code == 201
    assert response1.json()["id"] == response2.json()["id"]


@pytest.mark.asyncio
async def test_create_report_rollback_invalid_work_method():
    data = await _seed_full_report_scenario("rpt-5")
    # cannot use session from helper easily; test uses endpoint
    payload = _report_payload(
        object_id=data["obj_own"].id,
        stage_id=data["stage"].id,
        works=[
            {
                "work_type_id": data["work_type"].id,
                "work_method_id": 999999,
                "unit_id": data["unit"].id,
                "quantity": "10.00",
            }
        ],
    )
    response = client.post(
        "/api/reports",
        json=payload,
        headers={"Idempotency-Key": "key-rpt-5"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_report_detail():
    data = await _seed_full_report_scenario("rpt-6")
    payload = _report_payload(
        object_id=data["obj_own"].id,
        stage_id=data["stage"].id,
        equipment=[
            {
                "equipment_type_id": data["equipment"].id,
                "ownership": "own",
                "unit_id": data["unit"].id,
                "quantity": "1.00",
            }
        ],
    )
    response = client.post(
        "/api/reports",
        json=payload,
        headers={"Idempotency-Key": "key-rpt-6"},
    )
    report_id = response.json()["id"]

    detail_response = client.get(f"/api/reports/{report_id}")
    assert detail_response.status_code == 200
    body = detail_response.json()
    assert body["id"] == report_id
    assert len(body["equipment"]) == 1
    assert body["equipment"][0]["quantity"] == "1.00"
