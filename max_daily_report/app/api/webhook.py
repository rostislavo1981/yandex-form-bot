from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db as get_async_session
from app.models.catalogs import Object
from app.models.reports import DailyReport, ReportObligation
from app.models.users import User
from app.services.max_client import MAXClient

router = APIRouter(prefix="/api/webhook", tags=["webhook"])


def _verify_secret(x_max_bot_api_secret: str | None, secret: str) -> bool:
    if not secret:
        return False
    return x_max_bot_api_secret == secret


def _mini_app_url() -> str:
    """Public link to open the Mini App; never contains the bot token."""
    if settings.max_bot_username:
        return f"https://max.ru/{settings.max_bot_username}?startapp=report"
    return settings.webapp_public_url or ""


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
    user = event.get("user")
    if not user or not isinstance(user, dict):
        return None
    user_id = user.get("user_id") or user.get("id")
    name = user.get("name") or user.get("fullName") or "Пользователь"
    if not user_id:
        return None
    return str(user_id), str(name)


def _extract_chat_id(event: dict[str, Any]) -> str | None:
    chat_id = event.get("chat_id")
    if chat_id is not None:
        return str(chat_id)
    chat = event.get("chat")
    if isinstance(chat, dict):
        chat_id = chat.get("chat_id") or chat.get("id")
        if chat_id is not None:
            return str(chat_id)
    return None


def _build_start_keyboard() -> list[list[dict[str, Any]]]:
    return [
        [
            {"text": "Открыть форму отчёта", "callback_data": "open_report"},
            {"text": "Мои отчёты", "callback_data": "my_reports"},
        ]
    ]


async def _send(chat_id: str, text: str, keyboard: list | None = None) -> None:
    client = MAXClient()
    try:
        await client.send_message(chat_id=chat_id, text=text, inline_keyboard=keyboard)
    finally:
        await client.close()


async def _handle_open_report(chat_id: str) -> None:
    url = _mini_app_url()
    if url:
        text = f"Откройте Mini App для заполнения отчёта: {url}"
    else:
        text = "Откройте Mini App через кнопку «Заполнить отчёт» в меню бота."
    await _send(chat_id, text)


async def _handle_my_reports(
    session: AsyncSession, chat_id: str, max_user_id: str
) -> None:
    result = await session.execute(
        select(DailyReport, Object)
        .join(User, DailyReport.responsible_user_id == User.id)
        .join(Object, DailyReport.object_id == Object.id)
        .where(User.max_user_id == max_user_id)
        .order_by(DailyReport.report_date.desc(), DailyReport.id.desc())
        .limit(5)
    )
    rows = result.all()
    lines = [
        f"✅ {report.report_date}: {obj.code} — {obj.name}" for report, obj in rows
    ]
    text = (
        "Последние отчёты:\n" + "\n".join(lines)
        if lines
        else "Вы пока не отправляли отчётов."
    )
    await _send(chat_id, text)


async def _handle_group_status(session: AsyncSession, chat_id: str) -> None:
    from datetime import date

    today = date.today()
    counts_result = await session.execute(
        select(ReportObligation.status, func.count())
        .where(ReportObligation.report_date == today)
        .group_by(ReportObligation.status)
    )
    counts = dict(counts_result.all())
    expected = sum(counts.values())
    submitted = counts.get("submitted", 0) + counts.get("late", 0)
    pending = counts.get("pending", 0)
    text = (
        f"📊 Статус за {today}\n"
        f"Ожидается: {expected}, сдано: {submitted}, "
        f"с опозданием: {counts.get('late', 0)}, не сдано: {pending}"
    )
    await _send(chat_id, text)


@router.post("/max")
async def max_webhook(
    request: Request,
    x_max_bot_api_secret: str | None = Header(default=None),
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, str]:
    if not _verify_secret(x_max_bot_api_secret, settings.max_webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid secret")

    event = await request.json()
    update_type = event.get("update_type")

    if update_type == "bot_started":
        user_info = _extract_user(event)
        chat_id = _extract_chat_id(event)
        if user_info:
            await _get_or_create_user(session, user_info[0], user_info[1])
        if chat_id:
            await _send(
                chat_id,
                "Здравствуйте! Отправьте ежедневный отчёт прямо здесь.",
                keyboard=_build_start_keyboard(),
            )
        return {"status": "ok"}

    if update_type == "message_callback":
        callback = event.get("callback", {})
        callback_data = callback.get("payload", "")
        chat_id = _extract_chat_id(event)
        user_info = _extract_user(event)
        if user_info:
            await _get_or_create_user(session, user_info[0], user_info[1])
        if not chat_id:
            return {"status": "ignored"}

        if callback_data == "open_report":
            await _handle_open_report(chat_id)
            return {"status": "ok"}

        if callback_data == "my_reports" and user_info:
            await _handle_my_reports(session, chat_id, user_info[0])
            return {"status": "ok"}

        if callback_data.startswith("group_status"):
            await _handle_group_status(session, chat_id)
            return {"status": "ok"}

        if callback_data.startswith(("timesheet", "timesheet_excel")):
            url = _mini_app_url()
            text = (
                f"Табель доступен в Mini App: {url}"
                if url
                else "Табель доступен в Mini App — откройте бота."
            )
            await _send(chat_id, text)
            return {"status": "ok"}

    return {"status": "ignored"}
