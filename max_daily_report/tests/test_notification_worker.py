from __future__ import annotations

import json
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.catalogs import Object
from app.models.reports import DailyReport, NotificationLog, OutboxEvent, ReportWork
from app.models.users import MAXGroup, User
from app.services.notification_worker import NotificationWorker


async def _seed(session) -> tuple[User, Object, MAXGroup, DailyReport]:
    from datetime import date

    from app.models.catalogs import Stage, Unit, WorkType

    user = User(max_user_id="max-1", full_name="Иван Иванов", role="responsible")
    obj = Object(code="OBJ-1", name="Объект 1", active=True)
    stage = Stage(code="STG-1", name="Этап 1", active=True)
    unit = Unit(code="m3", name="кубометр", symbol="м³", active=True)
    work_type = WorkType(code="WT-1", name="Работа 1", active=True)
    group = MAXGroup(chat_id="chat-1", title="Группа", active=True)
    session.add_all([user, obj, stage, unit, work_type, group])
    await session.flush()

    report = DailyReport(
        report_date=date(2026, 7, 14),
        responsible_user_id=user.id,
        object_id=obj.id,
        stage_id=stage.id,
        staff_itr=1,
        staff_internal=2,
        staff_external=3,
        status="submitted",
        idempotency_key="key-1",
    )
    session.add(report)
    await session.flush()

    work = ReportWork(
        report_id=report.id,
        work_type_id=work_type.id,
        work_name_snapshot="Работа 1",
        unit_id=unit.id,
        unit_name_snapshot="м³",
        quantity=Decimal("12.50"),
    )
    session.add(work)
    await session.flush()
    return user, obj, group, report


@pytest.mark.asyncio
async def test_process_report_submitted_creates_notification(async_session):
    worker = NotificationWorker(async_session)
    user, obj, group, report = await _seed(async_session)
    event = OutboxEvent(
        event_key=f"report_submitted:{report.id}",
        kind="report_submitted",
        payload_json=json.dumps({"report_id": report.id}),
        status="pending",
    )
    async_session.add(event)
    await async_session.commit()

    with patch("app.services.notification_worker.MAXClient") as MockClient:
        instance = MockClient.return_value
        instance.send_message = AsyncMock(return_value={"message_id": "msg-123"})
        instance.close = AsyncMock()
        with patch.object(worker, "_refresh_group_panel", new=AsyncMock()):
            result = await worker.process_pending()

    assert result["success"] == 1
    log_result = await async_session.execute(
        select(NotificationLog).where(NotificationLog.notification_key == f"report:{report.id}:{group.id}")
    )
    log = log_result.scalar_one()
    assert log.status == "sent"
    assert log.external_message_id == "msg-123"
    assert log.group_id == group.id

    text = instance.send_message.await_args.kwargs["text"]
    assert "Иван Иванов" in text
    assert "Объект 1" in text
    assert "12.5" in text


@pytest.mark.asyncio
async def test_idempotency_no_duplicate_send(async_session):
    worker = NotificationWorker(async_session)
    user, obj, group, report = await _seed(async_session)
    log = NotificationLog(
        notification_key=f"report:{report.id}:{group.id}",
        kind="report_submitted",
        group_id=group.id,
        report_date=report.report_date,
        status="sent",
        external_message_id="existing",
    )
    async_session.add(log)
    event = OutboxEvent(
        event_key=f"report_submitted:{report.id}",
        kind="report_submitted",
        payload_json=json.dumps({"report_id": report.id}),
        status="pending",
    )
    async_session.add(event)
    await async_session.commit()

    with patch("app.services.notification_worker.MAXClient") as MockClient:
        instance = MockClient.return_value
        instance.send_message = AsyncMock()
        instance.close = AsyncMock()
        result = await worker.process_pending()

    assert result["success"] == 1
    instance.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_temporary_failure_retries(async_session):
    worker = NotificationWorker(async_session)
    user, obj, group, report = await _seed(async_session)
    event = OutboxEvent(
        event_key=f"report_submitted:{report.id}",
        kind="report_submitted",
        payload_json=json.dumps({"report_id": report.id}),
        status="pending",
    )
    async_session.add(event)
    await async_session.commit()

    with patch("app.services.notification_worker.MAXClient") as MockClient:
        instance = MockClient.return_value
        instance.send_message = AsyncMock(side_effect=RuntimeError("MAX timeout"))
        instance.close = AsyncMock()
        result = await worker.process_pending()

    assert result["failed"] == 1
    await async_session.refresh(event)
    assert event.status == "pending"
    assert event.attempts == 1
