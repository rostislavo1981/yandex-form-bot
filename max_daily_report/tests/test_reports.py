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
from app.services.obligation_service import generate_obligations

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

        # Generate obligations for today so submission-status endpoint has data.
        async with AsyncSessionLocal() as obligation_session:
            await generate_obligations(
                obligation_session, date(2026, 7, 14), date(2026, 7, 14)
            )

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


async def _generate_obligations_today():
    async with AsyncSessionLocal() as obligation_session:
        await generate_obligations(
            obligation_session, date(2026, 7, 14), date(2026, 7, 14)
        )


async def _seed_second_user_with_assignment(suffix: str):
    async with AsyncSessionLocal() as session:
        user = User(
            max_user_id=f"dev-user-2-{suffix}",
            full_name=f"Other User {suffix}",
            role="responsible",
        )
        session.add(user)
        await session.flush()

        obj = Object(code=f"obj-other-{suffix}", name="Другой объект", execution_method="own")
        stage = Stage(code=f"stg-other-{suffix}", name="Другой этап")
        session.add_all([obj, stage])
        await session.flush()

        session.add_all(
            [
                ObjectStage(object_id=obj.id, stage_id=stage.id),
                ResponsibleObjectAssignment(
                    user_id=user.id,
                    object_id=obj.id,
                    active_from=date(2026, 1, 1),
                    active_to=date(2026, 12, 31),
                    schedule_type="daily",
                ),
            ]
        )
        await session.commit()
        return {"user": user, "object": obj, "stage": stage}


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


@pytest.mark.asyncio
async def test_list_reports_filters_by_user():
    # dev-user always gets the "dev-user" persisted fixture from middleware
    data = await _seed_full_report_scenario("rpt-list-1")
    other = await _seed_second_user_with_assignment("rpt-list-2")

    # first report as dev-user
    payload1 = _report_payload(
        object_id=data["obj_own"].id,
        stage_id=data["stage"].id,
        staff={"itr": 1, "internal": 0, "external": 0},
    )
    response1 = client.post(
        "/api/reports",
        json=payload1,
        headers={"Idempotency-Key": "key-rpt-list-1"},
    )
    assert response1.status_code == 201

    # second report as the other user — endpoint always uses dev-user middleware,
    # so we create the report directly through the service to simulate another user.
    from app.schemas.reports import ReportCreateRequest
    from app.services.report_service import ReportService

    async with AsyncSessionLocal() as session:
        other_user = await session.merge(other["user"])
        service = ReportService(session)
        payload = _report_payload(
            report_date="2026-07-13",
            object_id=other["object"].id,
            stage_id=other["stage"].id,
            staff={"itr": 2, "internal": 0, "external": 0},
        )
        await service.create(
            other_user,
            ReportCreateRequest(**payload),
            "key-rpt-list-2",
        )

    list_response = client.get("/api/reports")
    assert list_response.status_code == 200
    body = list_response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["object_id"] == data["obj_own"].id


@pytest.mark.asyncio
async def test_list_reports_date_filter():
    data = await _seed_full_report_scenario("rpt-date")
    payload1 = _report_payload(
        report_date="2026-07-10",
        object_id=data["obj_own"].id,
        stage_id=data["stage"].id,
        staff={"itr": 1, "internal": 0, "external": 0},
    )
    payload2 = _report_payload(
        report_date="2026-07-12",
        object_id=data["obj_own"].id,
        stage_id=data["stage"].id,
        staff={"itr": 1, "internal": 0, "external": 0},
    )
    client.post(
        "/api/reports",
        json=payload1,
        headers={"Idempotency-Key": "key-rpt-date-1"},
    )
    client.post(
        "/api/reports",
        json=payload2,
        headers={"Idempotency-Key": "key-rpt-date-2"},
    )

    response = client.get("/api/reports?date_from=2026-07-11&date_to=2026-07-15")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["report_date"] == "2026-07-12"


@pytest.mark.asyncio
async def test_submission_status_counts_pending_and_submitted():
    data = await _seed_full_report_scenario("rpt-status")
    # obligations already generated by seed for two objects on today's date
    status_response = client.get("/api/submission-status?date=2026-07-14")
    assert status_response.status_code == 200
    body = status_response.json()
    assert body["expected"] == 2
    assert body["submitted"] == 0
    assert body["pending"] == 2
    assert body["late"] == 0
    assert len(body["missing"]) == 2

    # submit one report
    payload = _report_payload(
        object_id=data["obj_own"].id,
        stage_id=data["stage"].id,
        staff={"itr": 1, "internal": 0, "external": 0},
    )
    client.post(
        "/api/reports",
        json=payload,
        headers={"Idempotency-Key": "key-rpt-status-submit"},
    )

    status_response = client.get("/api/submission-status?date=2026-07-14")
    assert status_response.status_code == 200
    body = status_response.json()
    assert body["expected"] == 2
    # после F4.4 сдача после due_at помечается late; тест не привязан
    # к реальному времени, поэтому считаем «сдано» = submitted + late
    assert body["submitted"] + body["late"] == 1
    assert body["pending"] == 1
    assert len(body["missing"]) == 1
