"""MAX bot commands — webapp button, summary, help."""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import date as _date
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlencode

from backend.db import SubmissionDAO
from backend.excel.summary import build_summary
from backend.max import MaxClient, MaxError
from backend.schemas import Report

logger = logging.getLogger(__name__)


HELP_TEXT = (
    "🤖 Яндекс Формы Бот\n\n"
    "Команды:\n"
    "/help — это сообщение\n"
    "/summary [YYYY-MM-DD] — Excel-сводная за день\n"
    "/webapp — открыть мини-приложение со сводной\n\n"
    "Любой другой текст = отчёт прораба → парсится и заполняет форму."
)


def get_webapp_url() -> str:
    """Public URL of the Mini App. Read from env, default to local."""
    base = os.getenv("WEBAPP_PUBLIC_URL", "https://bot.example.com")
    return f"{base.rstrip('/')}/miniapp/index.html"


def _build_webapp_url(params: dict[str, str] | None = None) -> str:
    base = get_webapp_url()
    if not params:
        return base
    return f"{base}?{urlencode(params)}"


async def send_webapp_button(
    max_client: MaxClient, chat_id: int | str, *, date_to: str | None = None
) -> None:
    """Send a message with a button that opens the Mini App.

    Falls back to plain message if WebApp launch not supported by MAX yet.
    """
    url = _build_webapp_url({"date_to": date_to} if date_to else None)
    text = f"📊 Открыть сводную (сводка до {date_to or 'сегодня'})"
    try:
        # Try WebApp button first (Telegram-compatible API)
        await max_client._call(  # type: ignore[attr-defined]
            "sendMessage",
            chat_id=str(chat_id),
            text=text,
            reply_markup={
                "inline_keyboard": [
                    [{"text": "📊 Открыть мини-приложение", "web_app": {"url": url}}]
                ]
            },
        )
    except (MaxError, AttributeError, KeyError) as e:
        logger.warning("webapp button failed (%s); sending plain URL", e)
        await max_client.send_message(chat_id, f"{text}\n{url}")


async def handle_webapp_command(
    chat_id: int | str, *, max_client: MaxClient
) -> None:
    """/webapp → отправить кнопку открытия Mini App."""
    today = _date.today().isoformat()
    await send_webapp_button(max_client, chat_id, date_to=today)


async def handle_summary_command(
    chat_id: int | str,
    cmd: str,
    *,
    max_client: MaxClient,
    dao: SubmissionDAO,
    data_dir: Path,
) -> None:
    """/summary [YYYY-MM-DD] → build Excel, send as document."""
    parts = cmd.split(maxsplit=1)
    if len(parts) > 1:
        try:
            target = _date.fromisoformat(parts[1])
        except ValueError:
            await max_client.send_message(chat_id, "❌ Неверная дата. Формат: YYYY-MM-DD")
            return
    else:
        target = _date.today() - timedelta(days=1)

    rows = await asyncio.to_thread(dao.list_by_date, target.isoformat(), target.isoformat())
    if not rows:
        await max_client.send_message(chat_id, f"За {target.isoformat()} отчётов нет.")
        return

    pairs = [(Report.model_validate(r.report), bool(r.screenshot_path)) for r in rows]
    out = data_dir / f"summary_{target.isoformat()}.xlsx"
    try:
        await asyncio.to_thread(build_summary, pairs, out)
    except Exception as e:  # noqa: BLE001
        await max_client.send_message(chat_id, f"❌ Ошибка сборки xlsx: {e}")
        return

    try:
        await max_client.send_document(chat_id, str(out), caption=f"Сводная за {target}")
    except MaxError as e:
        await max_client.send_message(chat_id, f"❌ Не удалось отправить файл: {e}")
