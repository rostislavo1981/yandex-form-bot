from __future__ import annotations

from datetime import date, datetime, time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.config import settings
from app.main import create_app
from app.models.catalogs import EquipmentType, Object, Stage, Unit, WorkType
from app.models.reports import DailyReport, ReportObligation, ResponsibleObjectAssignment
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


def _seed_morning_summary(db_session):
    dev_user = User(max_user_id="dev-user", full_name="Dev User", role="manager")
    group = MAXGroup(chat_id="chat-morning", title="Утренняя группа", active=True)
    db_session.add_all([dev_user, group])
    db_session.flush()

    users = [
        User(max_user_id="u1", full_name="Иван", role="responsible"),
        User(max_user_id="u2", full_name="Пётр", role="responsible"),
        User(max_user_id="u3", full_name="Анна", role="responsible"),
    ]
    objects = [Object(code=f"OBJ-{i}", name=f"Объект {i}", active=True) for i in range(1, 5)]
    db_session.add_all(users + objects)
    db_session.flush()

    assignments = []
    for user in users:
        for obj in objects:
            assignments.append(
                ResponsibleObjectAssignment(
                    user_id=user.id,
                    object_id=obj.id,
                    active_from=date(2026, 7, 1),
                    active_to=date(2026, 7, 31),
                    schedule_type="daily",
                )
            )
    db_session.add_all(assignments)
    db_session.flush()

    target = date(2026, 7, 13)
    statuses = ["submitted"] * 8 + ["late"] + ["pending"] * 3
    for idx, assignment in enumerate(assignments):
        db_session.add(
            ReportObligation(
                report_date=target,
                assignment_id=assignment.id,
                user_id=assignment.user_id,
                object_id=assignment.object_id,
                status=statuses[idx],
                due_at=datetime.combine(target, time(23, 59, 59)),
            )
        )
    db_session.flush()
    db_session.commit()
    return group, target, users, objects


def test_morning_summary(client: TestClient, db_session):
    group, target, users, objects = _seed_morning_summary(db_session)

    with patch("app.services.scheduler_service.MAXClient") as MockClient:
        instance = MockClient.return_value
        instance.send_message = AsyncMock(return_value={"msgId": "msg-morning"})
        instance.close = AsyncMock()
        response = client.post(
            f"/api/scheduler/morning-summary?group_id={group.id}&target_date={target.isoformat()}"
        )

    assert response.status_code == 200
    data = response.json()
    assert data["sent"] == 1
    assert data["expected"] == 12
    assert data["submitted"] == 9  # 8 submitted + 1 late counted as submitted
    assert data["late"] == 1
    assert data["missed"] == 3  # pending became missed

    instance.send_message.assert_awaited_once()
    text = instance.send_message.await_args.kwargs["text"]
    assert "Утренняя сводка" in text
    assert "Всего: 12" in text
    assert "сдано: 9" in text
    assert "с опозданием: 1" in text
    assert "пропущено: 3" in text

    keyboard = instance.send_message.await_args.kwargs["inline_keyboard"]
    flat = [btn["callback_data"] for row in keyboard for btn in row]
    assert any("group_status:" in cd for cd in flat)
    assert any("timesheet:" in cd for cd in flat)
    assert any("timesheet_excel:" in cd for cd in flat)

    # pending obligations were converted to missed
    pending_count = db_session.execute(
        select(func.count())
        .select_from(ReportObligation)
        .where(ReportObligation.report_date == target)
        .where(ReportObligation.status == "pending")
    ).scalar()
    assert pending_count == 0

    missed_count = db_session.execute(
        select(func.count())
        .select_from(ReportObligation)
        .where(ReportObligation.report_date == target)
        .where(ReportObligation.status == "missed")
    ).scalar()
    assert missed_count == 3


def test_morning_summary_skipped_on_repeat(client: TestClient, db_session):
    group, target, _users, _objects = _seed_morning_summary(db_session)

    with patch("app.services.scheduler_service.MAXClient") as MockClient:
        instance = MockClient.return_value
        instance.send_message = AsyncMock(return_value={"msgId": "msg-morning"})
        instance.close = AsyncMock()
        client.post(f"/api/scheduler/morning-summary?group_id={group.id}&target_date={target.isoformat()}")

    with patch("app.services.scheduler_service.MAXClient") as MockClient:
        instance = MockClient.return_value
        instance.send_message = AsyncMock()
        instance.close = AsyncMock()
        response = client.post(
            f"/api/scheduler/morning-summary?group_id={group.id}&target_date={target.isoformat()}"
        )
    assert response.json()["skipped"] == 1
    instance.send_message.assert_not_awaited()
