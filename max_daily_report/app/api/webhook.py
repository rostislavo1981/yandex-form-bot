from __future__ import annotations

import hashlib
import hmac
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db as get_async_session
from app.models.reports import DailyReport
from app.models.users import User
from app.services.max_client import MAXClient

router = APIRouter(prefix="/api/webhook", tags=["webhook"])


def _verify_secret(payload: bytes, signature: str, secret: str) -> bool:
    if not secret or not signature:
        return False
    digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest.lower(), signature.lower())


async def _get_or_create_user(
    session: AsyncSession, max_user_id: str, full_name: str
) -> User:
    result = await session.execute(
        select(User).where(User.max_user_id == max_user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        user = User(max_user_id=max_user_id, full_name=full_name, role="responsible")
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


def _extract_user(event: dict[str, Any]) -> tuple[str, str] | None:
    sender = event.get("sender") or event.get("user") or event.get("from")
    if not sender or not isinstance(sender, dict):
        return None
    user_id = sender.get("userId") or sender.get("id")
    name = sender.get("name") or sender.get("fullName") or "Пользователь"
    if not user_id:
        return None
    return str(user_id), str(name)


def _extract_chat_id(event: dict[str, Any]) -> str | None:
    chat = event.get("chat")
    if isinstance(chat, dict):
        return chat.get("chatId") or chat.get("id")
    return event.get("chatId") or event.get("groupId")


def _build_start_keyboard() -> list[list[dict[str, Any]]]:
    return [
        [
            {"text": "Открыть форму отчёта", "callback_data": "open_report"},
            {"text": "Мои отчёты", "callback_data": "my_reports"},
        ]
    ]


@router.post("/max")
async def max_webhook(
    request: Request,
    x_signature: str | None = Header(default=None, alias="x-signature"),
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, str]:
    payload = await request.body()
    if not _verify_secret(payload, x_signature or "", settings.max_webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = await request.json()
    event_type = event.get("type") or event.get("event")

    if event_type == "bot_started":
        user_info = _extract_user(event)
        chat_id = _extract_chat_id(event)
        if user_info:
            await _get_or_create_user(session, user_info[0], user_info[1])
        if chat_id:
            client = MAXClient()
            await client.send_message(
                chat_id=chat_id,
                text="Здравствуйте! Отправьте ежедневный отчёт прямо здесь.",
                inline_keyboard=_build_start_keyboard(),
            )
            await client.close()
        return {"status": "ok"}

    if event_type == "callback":
        callback_data = event.get("callbackData") or event.get("payload")
        chat_id = _extract_chat_id(event)
        user_info = _extract_user(event)
        if user_info:
            await _get_or_create_user(session, user_info[0], user_info[1])

        if callback_data == "open_report" and chat_id:
            url = f"https://t.me/{settings.max_bot_token.split(':')[0]}?startapp=report"
            client = MAXClient()
            await client.send_message(
                chat_id=chat_id,
                text=f"Откройте Mini App для заполнения отчёта: {url}",
            )
            await client.close()
            return {"status": "ok"}

        if callback_data == "my_reports" and user_info:
            user_id = user_info[0]
            result = await session.execute(
                select(DailyReport)
                .where(DailyReport.user_id == user_id)
                .order_by(DailyReport.report_date.desc())
                .limit(5)
            )
            reports = result.scalars().all()
            lines = []
            for r in reports:
                status = "✅" if r.submitted_at else "⏳"
                lines.append(f"{status} {r.report_date}: {r.object_name}")
            text = (
                "Последние отчёты:\n" + "\n".join(lines)
                if lines
                else "Вы пока не отправляли отчётов."
            )
            if chat_id:
                client = MAXClient()
                await client.send_message(chat_id=chat_id, text=text)
                await client.close()
            return {"status": "ok"}

    return {"status": "ignored"}
