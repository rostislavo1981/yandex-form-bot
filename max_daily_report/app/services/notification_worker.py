from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.catalogs import Object
from app.models.reports import DailyReport, NotificationLog, OutboxEvent
from app.models.users import MAXGroup, User
from app.services.control_panel_service import ControlPanelService
from app.services.max_client import MAXClient

MAX_ATTEMPTS = 5
BASE_BACKOFF_SECONDS = 30


class NotificationWorker:
    """Process pending outbox events and publish report cards to MAX."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def process_pending(self, limit: int = 50) -> dict[str, int]:
        events = await self._claim_events(limit)
        processed = {"success": 0, "failed": 0, "skipped": 0}
        for event in events:
            try:
                await self._process_event(event)
                event.status = "done"
                processed["success"] += 1
            except Exception as exc:  # noqa: BLE001
                event.attempts += 1
                event.last_error = str(exc)[:1000]
                if event.attempts >= MAX_ATTEMPTS:
                    event.status = "failed"
                else:
                    backoff = BASE_BACKOFF_SECONDS * (2 ** (event.attempts - 1))
                    event.available_at = datetime.now(UTC) + timedelta(seconds=backoff)
                    event.status = "pending"
                processed["failed"] += 1
            await self._session.flush()
        await self._session.commit()
        return processed

    async def _claim_events(self, limit: int) -> list[OutboxEvent]:
        now = datetime.now(UTC)
        subq = (
            select(OutboxEvent.id)
            .where(OutboxEvent.status == "pending")
            .where(OutboxEvent.available_at <= now)
            .order_by(OutboxEvent.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
            .subquery()
        )
        result = await self._session.execute(
            update(OutboxEvent)
            .where(OutboxEvent.id.in_(select(subq.c.id)))
            .values(status="processing")
            .returning(OutboxEvent.id)
        )
        claimed_ids = [row[0] for row in result.fetchall()]
        if not claimed_ids:
            return []
        result = await self._session.execute(
            select(OutboxEvent).where(OutboxEvent.id.in_(claimed_ids))
        )
        return list(result.scalars().all())

    async def _process_event(self, event: OutboxEvent) -> None:
        if event.kind == "report_submitted":
            await self._process_report_submitted(event)
        elif event.kind == "control_panel_refresh":
            await self._process_control_panel_refresh(event)

    async def _process_report_submitted(self, event: OutboxEvent) -> None:
        payload = json.loads(event.payload_json or "{}")
        report_id = payload.get("report_id")
        if not report_id:
            return

        result = await self._session.execute(
            select(DailyReport)
            .where(DailyReport.id == report_id)
            .options(selectinload(DailyReport.works), selectinload(DailyReport.equipment))
        )
        report = result.scalar_one_or_none()
        if report is None:
            return

        user = await self._session.get(User, report.responsible_user_id)
        obj = await self._session.get(Object, report.object_id)
        group = await self._get_active_group()
        if group is None:
            return

        key = f"report:{report.id}:{group.id}"
        log = await self._get_or_create_log(key, "report_submitted", group.id, report.report_date)
        if log.status == "sent" and log.external_message_id:
            return

        client = MAXClient()
        try:
            text = self._report_card_text(report, user, obj)
            keyboard = [
                [
                    {"text": "📊 Статус", "callback_data": f"group_status:{group.id}"},
                ]
            ]
            result = await client.send_message(
                chat_id=group.chat_id,
                text=text,
                inline_keyboard=keyboard,
            )
            message_id = result.get("message_id", "")
            log.status = "sent"
            log.external_message_id = message_id
            log.sent_at = datetime.now(UTC)
            log.attempts += 1
            await self._session.flush()
            if group.control_message_id:
                await self._refresh_group_panel(group)
        finally:
            await client.close()

    async def _process_control_panel_refresh(self, event: OutboxEvent) -> None:
        payload = json.loads(event.payload_json or "{}")
        group_id = payload.get("group_id")
        group = await self._session.get(MAXGroup, group_id)
        if group is None:
            return
        await self._refresh_group_panel(group)

    async def _refresh_group_panel(self, group: MAXGroup) -> None:
        service = ControlPanelService(self._session)
        await service.ensure_group_control_panel(group.id)

    async def _get_active_group(self) -> MAXGroup | None:
        result = await self._session.execute(
            select(MAXGroup).where(MAXGroup.active.is_(True)).limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_or_create_log(
        self,
        key: str,
        kind: str,
        group_id: int | None,
        report_date: Any | None,
    ) -> NotificationLog:
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
                status="pending",
            )
            self._session.add(log)
            await self._session.flush()
        return log

    def _report_card_text(self, report: DailyReport, user: User | None, obj: Object | None) -> str:
        lines = [
            f"✅ Отчёт #{report.id}",
            f"Дата: {report.report_date}",
            f"Объект: {report.object_name_snapshot}",
            f"Ответственный: {user.full_name if user else '—'}",
        ]
        if report.contract_full_name_snapshot:
            lines.append(f"Договор: {report.contract_full_name_snapshot}")
        # суммируем только внутри одной единицы измерения (правило спеки)
        work_totals = self._totals_by_unit(
            (w.unit_name_snapshot, w.quantity) for w in report.works
        )
        eq_totals = self._totals_by_unit(
            (e.unit_name_snapshot, e.quantity) for e in report.equipment
        )
        if work_totals:
            lines.append(f"Работы: {work_totals}")
        if eq_totals:
            lines.append(f"Техника: {eq_totals}")
        if report.soil_export_m3:
            lines.append(f"Вывоз грунта: {self._format_decimal(report.soil_export_m3)} м³")
        if report.staff_itr or report.staff_internal or report.staff_external:
            lines.append(
                f"Персонал: ИТР {report.staff_itr}, штат {report.staff_internal}, внеш {report.staff_external}"
            )
        return "\n".join(lines)

    @classmethod
    def _totals_by_unit(cls, pairs) -> str:
        totals: dict[str, Decimal] = {}
        for unit_name, quantity in pairs:
            totals[unit_name] = totals.get(unit_name, Decimal(0)) + quantity
        return ", ".join(
            f"{cls._format_decimal(qty)} {unit}" for unit, qty in totals.items()
        )

    @staticmethod
    def _format_decimal(value: Decimal | int | None) -> str:
        if value is None:
            return "0"
        d = Decimal(value)
        if d == d.to_integral_value():
            return str(int(d))
        return str(d.normalize())
