"""F5 regression tests: notification failure upsert, card units."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.catalogs import Object
from app.models.reports import NotificationLog, ReportObligation
from app.models.users import MAXGroup, User
from app.services.notification_worker import NotificationWorker
from app.services.scheduler_service import SchedulerService


@pytest.fixture
def reminder_data(db_session):
    group = MAXGroup(chat_id="chat-f5", title="Группа F5")
    user = User(max_user_id="f5-u", full_name="Ждёт напоминания", role="responsible")
    obj = Object(code="obj-f5", name="Объект F5", execution_method="own")
    db_session.add_all([group, user, obj])
    db_session.flush()
    from app.models.reports import ResponsibleObjectAssignment

    assignment = ResponsibleObjectAssignment(
        user_id=user.id,
        object_id=obj.id,
        active_from=date(2026, 1, 1),
        active_to=date(2026, 12, 31),
        schedule_type="daily",
    )
    db_session.add(assignment)
    db_session.flush()
    db_session.add(
        ReportObligation(
            report_date=date(2026, 7, 14),
            assignment_id=assignment.id,
            user_id=user.id,
            object_id=obj.id,
            status="pending",
        )
    )
    db_session.commit()
    return {"group_id": group.id}


@pytest.mark.asyncio
async def test_repeated_reminder_failure_does_not_crash(reminder_data):
    """F5.1: два подряд сбоя отправки — upsert лога, attempts=2, без IntegrityError."""
    group_id = reminder_data["group_id"]

    with patch("app.services.scheduler_service.MAXClient") as MockClient:
        instance = MockClient.return_value
        instance.send_message = AsyncMock(side_effect=RuntimeError("MAX down"))
        instance.close = AsyncMock()

        for _ in range(2):
            async with AsyncSessionLocal() as session:
                service = SchedulerService(session)
                result = await service.run_evening_reminder(
                    group_id, 1, date(2026, 7, 14)
                )
                assert result == {"sent": 0, "skipped": 0}

    async with AsyncSessionLocal() as session:
        log_result = await session.execute(
            select(NotificationLog).where(
                NotificationLog.notification_key
                == f"evening_reminder_1:{group_id}:2026-07-14"
            )
        )
        log = log_result.scalar_one()
        assert log.status == "failed"
        assert log.attempts == 2


@pytest.mark.asyncio
async def test_reminder_succeeds_after_failure(reminder_data):
    """После сбоя следующий запуск может отправить успешно."""
    group_id = reminder_data["group_id"]

    with patch("app.services.scheduler_service.MAXClient") as MockClient:
        instance = MockClient.return_value
        instance.send_message = AsyncMock(side_effect=RuntimeError("MAX down"))
        instance.close = AsyncMock()
        async with AsyncSessionLocal() as session:
            await SchedulerService(session).run_evening_reminder(
                group_id, 1, date(2026, 7, 14)
            )

    with patch("app.services.scheduler_service.MAXClient") as MockClient:
        instance = MockClient.return_value
        instance.send_message = AsyncMock(return_value={"msgId": "m-1"})
        instance.close = AsyncMock()
        async with AsyncSessionLocal() as session:
            result = await SchedulerService(session).run_evening_reminder(
                group_id, 1, date(2026, 7, 14)
            )
            assert result["sent"] == 1


def test_report_card_does_not_mix_units():
    """F5.4: количества в карточке группируются по единицам."""
    text = NotificationWorker._totals_by_unit(
        [("м", Decimal("45")), ("шт", Decimal("3")), ("м", Decimal("5"))]
    )
    assert "50 м" in text
    assert "3 шт" in text
