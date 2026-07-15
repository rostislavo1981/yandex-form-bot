from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine
from app.models.catalogs import Object
from app.models.reports import NotificationLog, ReportObligation
from app.models.users import MAXGroup, User
from app.services.max_client import MAXClient


@asynccontextmanager
async def advisory_lock(lock_id: int) -> AsyncIterator[bool]:
    """Hold a PostgreSQL advisory lock on a dedicated connection.

    Session-level advisory locks are tied to a connection; commits inside the
    job must not release the lock, so it lives on its own connection for the
    whole `async with` block.
    """
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT pg_try_advisory_lock(:lock_id)").bindparams(lock_id=lock_id)
        )
        acquired = bool(result.scalar())
        try:
            yield acquired
        finally:
            if acquired:
                await conn.execute(
                    text("SELECT pg_advisory_unlock(:lock_id)").bindparams(
                        lock_id=lock_id
                    )
                )


class SchedulerService:
    """Scheduled jobs: create obligations and send reminder notifications."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def run_morning(self, target_date: date | None = None) -> dict[str, int]:
        from app.services.obligation_service import ObligationService

        target = target_date or date.today()
        service = ObligationService(self._session)
        created, skipped = await service.generate_for_date_range(target, target)
        return {"created": created, "skipped": skipped}

    async def run_evening_reminder(
        self,
        group_id: int,
        reminder_number: int,
        target_date: date | None = None,
    ) -> dict[str, int]:
        group = await self._session.get(MAXGroup, group_id)
        if group is None or not group.active:
            return {"sent": 0, "skipped": 0}

        target = target_date or date.today()
        key = f"evening_reminder_{reminder_number}:{group_id}:{target.isoformat()}"

        if await self._already_sent(key):
            return {"sent": 0, "skipped": 1}

        # pending obligations for target date in this group
        pending = await self._pending_obligations(group_id, target)
        if not pending:
            return {"sent": 0, "skipped": 0}

        lines = [f"⏰ Напоминание #{reminder_number}: не сданы отчёты за {target}"]
        for item in pending:
            lines.append(f"• {item['user_name']} — {item['object_code']}")
        text = "\n".join(lines)

        client = MAXClient()
        try:
            result = await client.send_message(
                chat_id=group.chat_id,
                text=text,
                inline_keyboard=[
                    [
                        {"text": "📊 Статус", "callback_data": f"group_status:{group_id}"},
                        {"text": "📝 Отправить отчёт", "callback_data": "open_report"},
                    ]
                ],
            )
            message_id = str(result.get("msgId") or result.get("messageId") or "")
            await self._record_sent(key, "evening_reminder", group_id, target, message_id)
            return {"sent": 1, "skipped": 0}
        except Exception as exc:  # noqa: BLE001
            await self._record_failed(key, "evening_reminder", group_id, target, str(exc))
            return {"sent": 0, "skipped": 0}
        finally:
            await client.close()

    async def run_morning_summary(
        self,
        group_id: int,
        target_date: date | None = None,
    ) -> dict[str, int]:
        """Send morning summary for the previous day (or explicit date).

        Converts any remaining pending obligations for that date to missed,
        computes counts and sends a group message with action buttons.
        """
        group = await self._session.get(MAXGroup, group_id)
        if group is None or not group.active:
            return {"sent": 0, "skipped": 0}

        target = target_date or (_today_for_group(group) - timedelta(days=1))
        key = f"morning_summary:{group_id}:{target.isoformat()}"

        if await self._already_sent(key):
            return {"sent": 0, "skipped": 1}

        # pending -> missed for the target date
        pending_result = await self._session.execute(
            select(ReportObligation).where(
                ReportObligation.report_date == target,
                ReportObligation.status == "pending",
            )
        )
        for obligation in pending_result.scalars().all():
            obligation.status = "missed"
        await self._session.flush()

        # status counts for target date
        counts_result = await self._session.execute(
            select(ReportObligation.status, func.count())
            .where(ReportObligation.report_date == target)
            .group_by(ReportObligation.status)
        )
        status_counts = dict(counts_result.all())
        late = status_counts.get("late", 0)
        submitted_status = status_counts.get("submitted", 0)
        submitted = submitted_status + late
        missed = status_counts.get("missed", 0)
        expected = submitted + missed

        # missing list
        missing_result = await self._session.execute(
            select(ReportObligation, User, Object)
            .join(User, ReportObligation.user_id == User.id)
            .join(Object, ReportObligation.object_id == Object.id)
            .where(ReportObligation.report_date == target)
            .where(ReportObligation.status.in_(["pending", "missed"]))
        )
        missing = [
            {"responsible": user.full_name, "object_code": obj.code}
            for _obligation, user, obj in missing_result.unique().all()
        ]

        lines = [
            f"📊 Утренняя сводка за {target}",
            f"Всего: {expected}, сдано: {submitted}, с опозданием: {late}, пропущено: {missed}",
        ]
        if missing:
            lines.append("")
            lines.append("Не сдано:")
            for item in missing:
                lines.append(f"• {item['responsible']} — {item['object_code']}")
        text = "\n".join(lines)

        client = MAXClient()
        try:
            result = await client.send_message(
                chat_id=group.chat_id,
                text=text,
                inline_keyboard=[
                    [
                        {"text": "📋 Статус", "callback_data": f"group_status:{group_id}"},
                        {"text": "📈 Табель", "callback_data": f"timesheet:{group_id}"},
                    ],
                    [
                        {"text": "📥 Excel", "callback_data": f"timesheet_excel:{group_id}"},
                    ],
                ],
            )
            message_id = str(result.get("msgId") or result.get("messageId") or "")
            await self._record_sent(key, "morning_summary", group_id, target, message_id)
            return {
                "sent": 1,
                "skipped": 0,
                "expected": expected,
                "submitted": submitted,
                "late": late,
                "missed": missed,
            }
        except Exception as exc:  # noqa: BLE001
            await self._record_failed(key, "morning_summary", group_id, target, str(exc))
            return {"sent": 0, "skipped": 0}
        finally:
            await client.close()

    async def _already_sent(self, key: str) -> bool:
        result = await self._session.execute(
            select(NotificationLog).where(
                NotificationLog.notification_key == key,
                NotificationLog.status == "sent",
            )
        )
        return result.scalar_one_or_none() is not None

    async def _pending_obligations(
        self,
        group_id: int,  # noqa: ARG002 — MVP: одна группа, фильтр по группе не нужен
        target_date: date,
    ) -> list[dict[str, Any]]:
        result = await self._session.execute(
            select(ReportObligation, User, Object)
            .join(User, ReportObligation.user_id == User.id)
            .join(Object, ReportObligation.object_id == Object.id)
            .where(ReportObligation.report_date == target_date)
            .where(ReportObligation.status == "pending")
        )
        items = []
        for _obligation, user, obj in result.unique().all():
            items.append(
                {
                    "user_name": user.full_name,
                    "object_code": obj.code,
                }
            )
        return items

    async def _record_sent(
        self,
        key: str,
        kind: str,
        group_id: int,
        report_date: date,
        message_id: str,
    ) -> None:
        """Upsert by notification_key — после сбоя запись уже существует."""
        result = await self._session.execute(
            select(NotificationLog).where(NotificationLog.notification_key == key)
        )
        log = result.scalar_one_or_none()
        if log is None:
            log = NotificationLog(
                notification_key=key,
                kind=kind,
                group_id=group_id,
                report_date=report_date,
                attempts=0,
            )
            self._session.add(log)
        log.status = "sent"
        log.external_message_id = message_id
        log.sent_at = datetime.now(UTC)
        log.attempts = (log.attempts or 0) + 1
        log.last_error = None
        await self._session.commit()

    async def _record_failed(
        self,
        key: str,
        kind: str,
        group_id: int,
        report_date: date,
        error: str,
    ) -> None:
        """Upsert failure by notification_key — повторный сбой не должен
        падать на UNIQUE(notification_key)."""
        result = await self._session.execute(
            select(NotificationLog).where(NotificationLog.notification_key == key)
        )
        log = result.scalar_one_or_none()
        if log is None:
            log = NotificationLog(
                notification_key=key,
                kind=kind,
                group_id=group_id,
                report_date=report_date,
                status="failed",
                attempts=0,
            )
            self._session.add(log)
        log.status = "failed"
        log.attempts = (log.attempts or 0) + 1
        log.last_error = error[:1000]
        await self._session.commit()


def _today_for_group(group: MAXGroup) -> date:
    import zoneinfo

    tz = zoneinfo.ZoneInfo(group.timezone or "Europe/Moscow")
    return datetime.now(tz).date()
