from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import settings
from app.main import create_app
from app.models.catalogs import EquipmentType, Object, Stage, Unit, WorkType
from app.models.reports import (
    DailyReport,
    ReportEquipment,
    ReportObligation,
    ReportWork,
    ResponsibleObjectAssignment,
)
from app.models.users import MAXGroup, User


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture(autouse=True)
def _dev_env(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "dev")
    monkeypatch.setattr(settings, "debug", True)


def _seed_timesheet(db_session):
    # create a known dev placeholder so middleware picks it up; tests can reassign max_user_id
    dev_user = User(max_user_id="dev-user", full_name="Dev User", role="responsible")
    db_session.add(dev_user)
    manager = User(max_user_id="max-mgr", full_name="Менеджер", role="manager")
    user = User(max_user_id="max-u1", full_name="Иван", role="responsible")
    obj_a = Object(code="OBJ-A", name="Объект A", active=True)
    obj_b = Object(code="OBJ-B", name="Объект B", active=True)
    stage = Stage(code="STG", name="Этап", active=True)
    unit_m3 = Unit(code="m3", name="м³", symbol="м³", active=True)
    unit_h = Unit(code="h", name="час", symbol="ч", active=True)
    eq_type = EquipmentType(code="EXC", name="Экскаватор", active=True)
    work_type = WorkType(code="DIG", name="Земляные работы", active=True)
    group = MAXGroup(chat_id="chat-1", title="Группа", active=True)
    db_session.add_all(
        [dev_user, manager, user, obj_a, obj_b, stage, unit_m3, unit_h, eq_type, work_type, group]
    )
    db_session.flush()

    assignment_a = ResponsibleObjectAssignment(
        user_id=user.id,
        object_id=obj_a.id,
        active_from=date(2026, 7, 1),
        active_to=date(2026, 7, 31),
        schedule_type="daily",
    )
    assignment_b = ResponsibleObjectAssignment(
        user_id=user.id,
        object_id=obj_b.id,
        active_from=date(2026, 7, 1),
        active_to=date(2026, 7, 31),
        schedule_type="daily",
    )
    db_session.add_all([assignment_a, assignment_b])
    db_session.flush()

    for d in [date(2026, 7, 14), date(2026, 7, 15)]:
        db_session.add(
            ReportObligation(
                report_date=d,
                assignment_id=assignment_a.id,
                user_id=user.id,
                object_id=obj_a.id,
                status="pending",
            )
        )
    db_session.flush()

    report_a1 = DailyReport(
        report_date=date(2026, 7, 14),
        responsible_user_id=user.id,
        object_id=obj_a.id,
        stage_id=stage.id,
        object_name_snapshot="Объект A",
        staff_itr=1,
        staff_internal=2,
        staff_external=1,
        status="submitted",
        idempotency_key="key-a1",
    )
    db_session.add(report_a1)
    db_session.flush()
    db_session.add(
        ReportEquipment(
            report_id=report_a1.id,
            equipment_type_id=eq_type.id,
            equipment_name_snapshot="Экскаватор",
            ownership="own",
            unit_id=unit_h.id,
            unit_name_snapshot="ч",
            quantity=Decimal("8.00"),
        )
    )
    db_session.add(
        ReportWork(
            report_id=report_a1.id,
            work_type_id=work_type.id,
            work_name_snapshot="Земляные работы",
            unit_id=unit_m3.id,
            unit_name_snapshot="м³",
            quantity=Decimal("120.50"),
        )
    )
    db_session.add(
        ReportWork(
            report_id=report_a1.id,
            work_type_id=work_type.id,
            work_name_snapshot="Земляные работы",
            unit_id=unit_m3.id,
            unit_name_snapshot="м³",
            quantity=Decimal("10.00"),
        )
    )

    report_a2 = DailyReport(
        report_date=date(2026, 7, 15),
        responsible_user_id=user.id,
        object_id=obj_a.id,
        stage_id=stage.id,
        object_name_snapshot="Объект A",
        staff_itr=0,
        staff_internal=1,
        staff_external=0,
        status="submitted",
        idempotency_key="key-a2",
    )
    db_session.add(report_a2)
    db_session.flush()
    db_session.add(
        ReportEquipment(
            report_id=report_a2.id,
            equipment_type_id=eq_type.id,
            equipment_name_snapshot="Экскаватор",
            ownership="own",
            unit_id=unit_h.id,
            unit_name_snapshot="ч",
            quantity=Decimal("4.00"),
        )
    )

    report_b = DailyReport(
        report_date=date(2026, 7, 14),
        responsible_user_id=user.id,
        object_id=obj_b.id,
        stage_id=stage.id,
        object_name_snapshot="Объект B",
        staff_itr=5,
        staff_internal=5,
        staff_external=5,
        status="submitted",
        idempotency_key="key-b",
    )
    db_session.add(report_b)
    db_session.flush()
    db_session.commit()
    return obj_a, obj_b, user, manager


def test_timesheet_manager_sees_object(client: TestClient, db_session):
    obj_a, obj_b, user, manager = _seed_timesheet(db_session)
    dev_user = db_session.execute(select(User).where(User.max_user_id == "dev-user")).scalar_one()
    dev_user.max_user_id = "other-dev"
    manager.max_user_id = "dev-user"
    db_session.commit()

    response = client.get(
        f"/api/timesheet/{obj_a.id}?date_from=2026-07-14&date_to=2026-07-15"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["object_code"] == "OBJ-A"
    assert data["days"] == ["2026-07-14", "2026-07-15"]

    work_rows = [r for r in data["rows"] if r["category"] == "work"]
    assert len(work_rows) == 1
    assert work_rows[0]["values"] == ["130.5", ""]
    assert work_rows[0]["total"] == "130.5"

    personnel_rows = [r for r in data["rows"] if r["category"] == "personnel"]
    assert personnel_rows[0]["values"] == ["4", "1"]
    assert personnel_rows[0]["total"] == "5"
    assert personnel_rows[0]["average"] == "2.5"
    assert personnel_rows[0]["max"] == "4"

    missing = data["missing_days"]
    assert "2026-07-15" not in missing  # report exists for day 15


def test_timesheet_responsible_only_assigned_object(client: TestClient, db_session):
    obj_a, obj_b, user, manager = _seed_timesheet(db_session)
    dev_user = db_session.execute(select(User).where(User.max_user_id == "dev-user")).scalar_one()
    dev_user.max_user_id = "other-dev"
    user.max_user_id = "dev-user"
    db_session.commit()

    response = client.get(
        f"/api/timesheet/{obj_a.id}?date_from=2026-07-14&date_to=2026-07-15"
    )
    assert response.status_code == 200

    response_b = client.get(
        f"/api/timesheet/{obj_b.id}?date_from=2026-07-14&date_to=2026-07-15"
    )
    assert response_b.status_code == 200


def test_timesheet_does_not_mix_objects(client: TestClient, db_session):
    obj_a, obj_b, user, manager = _seed_timesheet(db_session)
    dev_user = db_session.execute(select(User).where(User.max_user_id == "dev-user")).scalar_one()
    dev_user.max_user_id = "other-dev"
    manager.max_user_id = "dev-user"
    db_session.commit()

    response = client.get(
        f"/api/timesheet/{obj_a.id}?date_from=2026-07-14&date_to=2026-07-15"
    )
    data = response.json()
    work_rows = [r for r in data["rows"] if r["category"] == "work"]
    assert work_rows[0]["total"] == "130.5"
    assert "15" not in work_rows[0]["values"]


def test_timesheet_day_status(client: TestClient, db_session):
    obj_a, obj_b, user, manager = _seed_timesheet(db_session)
    dev_user = db_session.execute(select(User).where(User.max_user_id == "dev-user")).scalar_one()
    dev_user.max_user_id = "other-dev"
    manager.max_user_id = "dev-user"
    db_session.commit()

    response = client.get(
        f"/api/timesheet/{obj_a.id}?date_from=2026-07-14&date_to=2026-07-15"
    )
    data = response.json()
    day_status = data["day_status"]
    assert day_status["2026-07-14"] == "submitted"
    assert day_status["2026-07-15"] == "submitted"
