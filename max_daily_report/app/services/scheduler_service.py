from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalogs import Object
from app.models.reports import NotificationLog, ReportObligation
from app.models.users import MAXGroup, User
from app.services.max_client import MAXClient


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

    async def acquire_lock(self, lock_id: int) -> bool:
        result = await self._session.execute(
            text("SELECT pg_try_advisory_lock(:lock_id)").bindparams(lock_id=lock_id)
        )
        return bool(result.scalar())

    async def release_lock(self, lock_id: int) -> None:
        await self._session.execute(
            text("SELECT pg_advisory_unlock(:lock_id)").bindparams(lock_id=lock_id)
        )

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
        group_id: int,
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
        log = NotificationLog(
            notification_key=key,
            kind=kind,
            group_id=group_id,
            report_date=report_date,
            status="sent",
            external_message_id=message_id,
            sent_at=datetime.now(UTC),
        )
        self._session.add(log)
        await self._session.commit()

    async def _record_failed(
        self,
        key: str,
        kind: str,
        group_id: int,
        report_date: date,
        error: str,
    ) -> None:
        log = NotificationLog(
            notification_key=key,
            kind=kind,
            group_id=group_id,
            report_date=report_date,
            status="failed",
            last_error=error[:1000],
        )
        self._session.add(log)
        await self._session.commit()


def _today_for_group(group: MAXGroup) -> date:
    import zoneinfo

    tz = zoneinfo.ZoneInfo(group.timezone or "Europe/Moscow")
    return datetime.now(tz).date()
