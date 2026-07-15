"""F3 regression tests: report validation edge cases."""
from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.catalogs import Object, ObjectStage, Stage, Unit, WorkType
from app.models.reports import ResponsibleObjectAssignment
from app.models.users import User

client = TestClient(app)


@pytest.fixture
def scenario(db_session):
    user = User(max_user_id="dev-user", full_name="Dev", role="responsible")
    unit = Unit(code="m", name="метр", symbol="м")
    obj = Object(code="obj-f3", name="Объект F3", execution_method="own")
    stage = Stage(code="st-f3", name="Этап F3")
    work_type = WorkType(code="wt-f3", name="Работа F3", default_unit_id=None)
    db_session.add_all([user, unit, obj, stage])
    db_session.flush()
    work_type.default_unit_id = unit.id
    db_session.add(work_type)
    db_session.add(ObjectStage(object_id=obj.id, stage_id=stage.id))
    db_session.add(
        ResponsibleObjectAssignment(
            user_id=user.id,
            object_id=obj.id,
            active_from=date(2026, 1, 1),
            active_to=date(2026, 12, 31),
            schedule_type="daily",
        )
    )
    db_session.commit()
    return {"unit": unit, "obj": obj, "stage": stage, "work_type": work_type}


def _base_payload(scenario) -> dict:
    return {
        "report_date": "2026-07-14",
        "object_id": scenario["obj"].id,
        "stage_id": scenario["stage"].id,
        "staff": {"itr": 0, "internal": 0, "external": 0},
    }


def test_works_only_report_is_accepted(scenario):
    """F3.1: отчёт только с работами (без техники/персонала/грунта) проходит."""
    payload = _base_payload(scenario)
    payload["works"] = [
        {
            "work_type_id": scenario["work_type"].id,
            "unit_id": scenario["unit"].id,
            "quantity": "45.00",
        }
    ]
    response = client.post(
        "/api/reports", json=payload, headers={"Idempotency-Key": "f3-works-only"}
    )
    assert response.status_code == 201, response.text


def test_soil_zero_is_not_content(scenario):
    """F3.2: soil_export_m3=0 при пустом остальном — 422."""
    payload = _base_payload(scenario)
    payload["soil_export_m3"] = "0"
    response = client.post(
        "/api/reports", json=payload, headers={"Idempotency-Key": "f3-soil-zero"}
    )
    assert response.status_code == 422


def test_negative_staff_rejected(scenario):
    """F3.3: отрицательный персонал — 422."""
    payload = _base_payload(scenario)
    payload["staff"] = {"itr": -5, "internal": 0, "external": 0}
    response = client.post(
        "/api/reports", json=payload, headers={"Idempotency-Key": "f3-neg-staff"}
    )
    assert response.status_code == 422


def test_duplicate_day_report_returns_409(scenario):
    """F3.4: второй отчёт за тот же день/объект — 409, не 500."""
    payload = _base_payload(scenario)
    payload["staff"] = {"itr": 1, "internal": 0, "external": 0}
    first = client.post(
        "/api/reports", json=payload, headers={"Idempotency-Key": "f3-dup-1"}
    )
    assert first.status_code == 201

    second = client.post(
        "/api/reports", json=payload, headers={"Idempotency-Key": "f3-dup-2"}
    )
    assert second.status_code == 409
    assert "уже сдан" in second.text


def test_unknown_equipment_type_returns_422(scenario):
    """F3.5: несуществующий equipment_type_id — 422, не 500."""
    payload = _base_payload(scenario)
    payload["equipment"] = [
        {
            "equipment_type_id": 999999,
            "ownership": "own",
            "unit_id": scenario["unit"].id,
            "quantity": "1.00",
        }
    ]
    response = client.post(
        "/api/reports", json=payload, headers={"Idempotency-Key": "f3-bad-eq"}
    )
    assert response.status_code == 422


def test_unknown_unit_returns_422(scenario):
    """F3.5: несуществующий unit_id — 422, не 500."""
    payload = _base_payload(scenario)
    payload["works"] = [
        {
            "work_type_id": scenario["work_type"].id,
            "unit_id": 999999,
            "quantity": "5.00",
        }
    ]
    response = client.post(
        "/api/reports", json=payload, headers={"Idempotency-Key": "f3-bad-unit"}
    )
    assert response.status_code == 422
