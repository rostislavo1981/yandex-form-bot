from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reports import NotificationLog, OutboxEvent
from app.models.users import MAXGroup, User
from app.services.max_client import MAXClient


class ControlPanelService:
    """Manage group and private control panels in MAX chats."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ensure_group_control_panel(self, group_id: int) -> dict[str, Any]:
        group = await self._get_group(group_id)
        if group is None:
            return {"status": "error", "detail": "group not found"}

        text, keyboard = self._group_panel_content(group_id)
        client = MAXClient()
        try:
            if group.control_message_id:
                try:
                    await client.edit_message(
                        chat_id=group.chat_id,
                        message_id=group.control_message_id,
                        text=text,
                        inline_keyboard=keyboard,
                    )
                    return {"status": "ok", "message_id": group.control_message_id}
                except Exception:  # noqa: BLE001
                    # message may be deleted, fall through to create new
                    pass

            result = await client.send_message(
                chat_id=group.chat_id,
                text=text,
                inline_keyboard=keyboard,
            )
            message_id = str(result.get("msgId") or result.get("messageId") or "")
            if message_id:
                group.control_message_id = message_id
                await self._session.commit()
                await client.pin_message(chat_id=group.chat_id, message_id=message_id)
            return {"status": "ok", "message_id": message_id}
        finally:
            await client.close()

    async def ensure_private_control_panel(self, user_id: int) -> dict[str, Any]:
        user = await self._session.get(User, user_id)
        if user is None:
            return {"status": "error", "detail": "user not found"}
        if not user.max_user_id:
            return {"status": "error", "detail": "user has no max_user_id"}

        text, keyboard = self._private_panel_content(user)
        client = MAXClient()
        try:
            if user.private_control_message_id:
                try:
                    await client.edit_message(
                        chat_id=user.max_user_id,
                        message_id=user.private_control_message_id,
                        text=text,
                        inline_keyboard=keyboard,
                    )
                    return {"status": "ok", "message_id": user.private_control_message_id}
                except Exception:  # noqa: BLE001
                    pass

            result = await client.send_message(
                chat_id=user.max_user_id,
                text=text,
                inline_keyboard=keyboard,
            )
            message_id = str(result.get("msgId") or result.get("messageId") or "")
            if message_id:
                user.private_control_message_id = message_id
                await self._session.commit()
            return {"status": "ok", "message_id": message_id}
        finally:
            await client.close()

    async def refresh_group_panel_outbox(self, group_id: int, actor_user_id: int | None = None) -> None:
        event = OutboxEvent(
            event_key=f"control_panel_refresh:group:{group_id}",
            kind="control_panel_refresh",
            payload_json=json.dumps(
                {
                    "group_id": group_id,
                    "actor_user_id": actor_user_id,
                }
            ),
            status="pending",
        )
        self._session.add(event)
        await self._session.flush()

    async def record_notification(
        self,
        key: str,
        kind: str,
        group_id: int | None,
        report_date: Any | None,
        status: str = "pending",
        external_message_id: str | None = None,
    ) -> None:
        result = await self._session.execute(
            select(NotificationLog).where(NotificationLog.notification_key == key)
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            log = NotificationLog(
                notification_key=key,
                kind=kind,
                group_id=group_id,
                report_date=report_date,
                status=status,
                external_message_id=external_message_id,
            )
            self._session.add(log)
        else:
            existing.status = status
            existing.external_message_id = external_message_id or existing.external_message_id
        await self._session.flush()

    async def _get_group(self, group_id: int) -> MAXGroup | None:
        return await self._session.get(MAXGroup, group_id)

    def _group_panel_content(self, group_id: int) -> tuple[str, list[list[dict[str, Any]]]]:
        text = (
            "📋 Пульт управления отчётами\n"
            "\n"
            "Используйте кнопки для быстрого доступа:\n"
            "• Статус — кто сегодня сдал\n"
            "• Табель — сводка по работам\n"
            "• Excel — выгрузка табеля\n"
        )
        keyboard = [
            [
                {"text": "📊 Статус", "callback_data": f"group_status:{group_id}"},
                {"text": "📈 Табель", "callback_data": f"group_timesheet:{group_id}"},
            ],
            [
                {"text": "📁 Excel", "callback_data": f"group_excel:{group_id}"},
                {"text": "🔁 Обновить", "callback_data": f"group_refresh:{group_id}"},
            ],
        ]
        return text, keyboard

    def _private_panel_content(self, user: User) -> tuple[str, list[list[dict[str, Any]]]]:
        text = (
            f"👋 {user.full_name}, здравствуйте!\n"
            "\n"
            "Отправьте ежедневный отчёт или посмотрите статус."
        )
        keyboard = [
            [
                {"text": "📝 Отправить отчёт", "callback_data": "open_report"},
                {"text": "📊 Мой статус", "callback_data": "my_status"},
            ],
            [
                {"text": "📈 Мои отчёты", "callback_data": "my_reports"},
                {"text": "🔄 Обновить", "callback_data": "private_refresh"},
            ],
        ]
        return text, keyboard
