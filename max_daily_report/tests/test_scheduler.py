from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import settings
from app.main import create_app
from app.models.catalogs import EquipmentType, Object, Stage, Unit, WorkType
from app.models.reports import DailyReport, ReportObligation
from app.models.users import MAXGroup, User


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture(autouse=True)
def _dev_env(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "dev")
    monkeypatch.setattr(settings, "debug", True)


def _seed_scheduler(db_session):
    dev_user = User(max_user_id="dev-user", full_name="Dev User", role="manager")
    user = User(max_user_id="max-u1", full_name="Иван", role="responsible")
    obj_a = Object(code="OBJ-A", name="Объект A", active=True)
    obj_b = Object(code="OBJ-B", name="Объект B", active=True)
    stage = Stage(code="STG", name="Этап", active=True)
    unit = Unit(code="m3", name="м³", symbol="м³", active=True)
    eq_type = EquipmentType(code="EXC", name="Экскаватор", active=True)
    work_type = WorkType(code="DIG", name="Земляные работы", active=True)
    group = MAXGroup(chat_id="chat-1", title="Группа", active=True)
    db_session.add_all([dev_user, user, obj_a, obj_b, stage, unit, eq_type, work_type, group])
    db_session.flush()

    from app.models.reports import ResponsibleObjectAssignment

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

    report = DailyReport(
        report_date=date(2026, 7, 14),
        responsible_user_id=user.id,
        object_id=obj_a.id,
        stage_id=stage.id,
        staff_itr=1,
        staff_internal=2,
        staff_external=1,
        status="submitted",
        idempotency_key="key-1",
    )
    db_session.add(report)
    db_session.flush()
    db_session.commit()
    return group, user, obj_a, obj_b


def test_morning_generates_obligations(client: TestClient, db_session):
    _seed_scheduler(db_session)
    response = client.post("/api/scheduler/morning?target_date=2026-07-14")
    assert response.status_code == 200
    data = response.json()
    assert data["created"] == 2

    obligations = db_session.execute(select(ReportObligation)).scalars().all()
    assert len(obligations) == 2


def test_evening_reminder_sends_once(client: TestClient, db_session):
    group, user, obj_a, obj_b = _seed_scheduler(db_session)
    # create obligations
    client.post("/api/scheduler/morning?target_date=2026-07-14")

    # OBJ-A already has a report: mark its obligation submitted
    obligation_a = db_session.execute(
        select(ReportObligation).where(ReportObligation.object_id == obj_a.id)
    ).scalar_one()
    obligation_a.status = "submitted"
    db_session.commit()

    with patch("app.services.scheduler_service.MAXClient") as MockClient:
        instance = MockClient.return_value
        instance.send_message = AsyncMock(return_value={"msgId": "msg-1"})
        instance.close = AsyncMock()
        response = client.post(
            f"/api/scheduler/evening-reminder?group_id={group.id}&reminder_number=1&target_date=2026-07-14"
        )
    assert response.status_code == 200
    assert response.json()["sent"] == 1
    instance.send_message.assert_awaited_once()
    text = instance.send_message.await_args.kwargs["text"]
    assert "Иван" in text
    assert "OBJ-B" in text
    assert "OBJ-A" not in text  # already submitted

    # second call is skipped because notification key already used
    with patch("app.services.scheduler_service.MAXClient") as MockClient:
        instance = MockClient.return_value
        instance.send_message = AsyncMock()
        instance.close = AsyncMock()
        response = client.post(
            f"/api/scheduler/evening-reminder?group_id={group.id}&reminder_number=1&target_date=2026-07-14"
        )
    assert response.json()["skipped"] == 1
    instance.send_message.assert_not_awaited()


def test_evening_reminder_no_pending(client: TestClient, db_session):
    group, user, obj_a, obj_b = _seed_scheduler(db_session)
    client.post("/api/scheduler/morning?target_date=2026-07-14")

    # mark all obligations as submitted so there is nothing to remind about
    for obligation in db_session.execute(select(ReportObligation)).scalars().all():
        obligation.status = "submitted"
    db_session.commit()

    with patch("app.services.scheduler_service.MAXClient") as MockClient:
        instance = MockClient.return_value
        instance.send_message = AsyncMock(return_value={"msgId": "msg-1"})
        instance.close = AsyncMock()
        response = client.post(
            f"/api/scheduler/evening-reminder?group_id={group.id}&reminder_number=2&target_date=2026-07-14"
        )
    assert response.status_code == 200
    assert response.json()["sent"] == 0
