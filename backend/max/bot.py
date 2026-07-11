"""Long-polling bot loop.

Flow:
1. getUpdates(offset, timeout)
2. For each update with a text message, run pipeline
3. Reply with success/error
4. /summary [date] → build summary, send xlsx
5. /help → list commands
6. /start  → subscribe the sender to daily 20:00 reminder
7. /stop   → unsubscribe
"""
from __future__ import annotations

import asyncio
import json
import logging
import signal
from datetime import date as _date
from datetime import timedelta
from pathlib import Path
from typing import Any

from backend.config import get_settings
from backend.db import SubmissionDAO
from backend.disk import YandexDiskClient
from backend.excel.summary import build_summary
from backend.llm.client import YandexGPTClient
from backend.max import MaxClient, MaxError
from backend.pipeline import run_pipeline
from backend.schemas import Report

logger = logging.getLogger(__name__)


HELP_TEXT = (
    "🤖 Яндекс Формы Бот\n\n"
    "Команды:\n"
    "/help — это сообщение\n"
    "/start — подписаться на напоминание в 20:00 заполнить отчёт\n"
    "/stop — отписаться от напоминаний\n"
    "/summary [YYYY-MM-DD] — Excel-сводная за день (default: вчера)\n\n"
    "Любой другой текст = отчёт прораба → парсится и заполняет форму."
)

SUBSCRIBERS_FILENAME = "subscribers.json"


def _subscribers_path(data_dir: Path) -> Path:
    return data_dir / SUBSCRIBERS_FILENAME


def _load_subscribers_file(data_dir: Path) -> dict[str, str]:
    p = _subscribers_path(data_dir)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _save_subscribers_file(data_dir: Path, subs: dict[str, str]) -> None:
    p = _subscribers_path(data_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(subs, ensure_ascii=False, indent=2), encoding="utf-8")


def _subscribe(data_dir: Path, chat_id: str, name: str = "") -> bool:
    """Add chat_id to subscribers. Returns True if it was a new subscription."""
    subs = _load_subscribers_file(data_dir)
    if chat_id in subs:
        return False
    subs[chat_id] = name or chat_id
    _save_subscribers_file(data_dir, subs)
    return True


def _unsubscribe(data_dir: Path, chat_id: str) -> bool:
    """Remove chat_id. Returns True if it was subscribed."""
    subs = _load_subscribers_file(data_dir)
    if chat_id not in subs:
        return False
    subs.pop(chat_id, None)
    _save_subscribers_file(data_dir, subs)
    return True


async def handle_message(
    chat_id: int | str,
    text: str,
    *,
    max_client: MaxClient,
    pipeline_deps: dict[str, Any],
) -> None:
    """Dispatch one text message to the right handler."""
    stripped = text.strip()
    if not stripped:
        return
    if stripped.startswith("/help"):
        await max_client.send_message(chat_id, HELP_TEXT)
    elif stripped.startswith("/start"):
        await _handle_start(chat_id, stripped, max_client=max_client, **pipeline_deps)
    elif stripped.startswith("/stop"):
        await _handle_stop(chat_id, stripped, max_client=max_client, **pipeline_deps)
    elif stripped.startswith("/summary"):
        await _handle_summary(chat_id, stripped, max_client=max_client, **pipeline_deps)
    else:
        await _handle_report(chat_id, stripped, max_client=max_client, **pipeline_deps)


async def _handle_start(
    chat_id: int | str,
    _text: str,
    *,
    max_client: MaxClient,
    data_dir: Path,
) -> None:
    name = ""
    # We don't get a clean username, so display name = chat_id
    is_new = _subscribe(data_dir, str(chat_id), name)
    msg = (
        "✅ Подписка оформлена. Каждый день в 20:00 буду напоминать заполнить отчёт."
        if is_new
        else "Ты уже подписан на напоминания в 20:00. /stop — отписаться."
    )
    await max_client.send_message(chat_id, msg)


async def _handle_stop(
    chat_id: int | str,
    _text: str,
    *,
    max_client: MaxClient,
    data_dir: Path,
) -> None:
    was_subscribed = _unsubscribe(data_dir, str(chat_id))
    msg = (
        "❌ Подписка отменена. Напоминания больше не придут."
        if was_subscribed
        else "Ты не был подписан."
    )
    await max_client.send_message(chat_id, msg)


async def _handle_report(
    chat_id: int | str,
    text: str,
    *,
    max_client: MaxClient,
    llm: Any,
    form_client: Any,
    disk_client: YandexDiskClient | None,
    form_url: str,
    screenshot_dir: Path,
    dao: SubmissionDAO,
    default_foreman: str,
) -> None:
    await max_client.send_message(chat_id, "⏳ Парсю отчёт и заполняю форму…")
    try:
        if hasattr(form_client, "__aenter__"):
            async with form_client as fc:
                res = await run_pipeline(
                    text,
                    llm=llm,
                    form_client=fc,
                    disk_client=disk_client,
                    form_url=form_url,
                    screenshot_dir=screenshot_dir,
                    dao=dao,
                    default_foreman=default_foreman,
                )
        else:
            res = await run_pipeline(
                text,
                llm=llm,
                form_client=form_client,
                disk_client=disk_client,
                form_url=form_url,
                screenshot_dir=screenshot_dir,
                dao=dao,
                default_foreman=default_foreman,
            )
            if hasattr(form_client, "close"):
                await form_client.close()
    except Exception as e:  # noqa: BLE001 — bot must not crash on bad input
        logger.exception("pipeline exception")
        await max_client.send_message(chat_id, f"❌ Ошибка: {e}")
        return

    if res.ok:
        msg = (
            f"✅ Отправлено\n"
            f"📅 {res.report.date}\n"
            f"🏗 {res.report.object_name}\n"
            f"👤 {res.report.foreman}\n"
            f"📸 Скриншот: {res.screenshot}\n"
        )
        if res.disk_json_url:
            msg += f"💾 Диск: {res.disk_json_url}\n"
    else:
        msg = f"❌ Не удалось: {res.error}"
    await max_client.send_message(chat_id, msg)


async def _handle_summary(
    chat_id: int | str,
    cmd: str,
    *,
    max_client: MaxClient,
    dao: SubmissionDAO,
    data_dir: Path,
) -> None:
    parts = cmd.split(maxsplit=1)
    if len(parts) > 1:
        try:
            target = _date.fromisoformat(parts[1])
        except ValueError:
            await max_client.send_message(chat_id, "❌ Неверная дата. Формат: YYYY-MM-DD")
            return
    else:
        target = (_date.today() - timedelta(days=1))  # вчера по умолчанию

    rows = await asyncio.to_thread(dao.list_by_date, target.isoformat(), target.isoformat())
    if not rows:
        await max_client.send_message(chat_id, f"За {target.isoformat()} отчётов нет.")
        return

    pairs = [(Report.model_validate(r.report), bool(r.screenshot_path)) for r in rows]
    out_path = data_dir / f"summary_{target.isoformat()}.xlsx"
    try:
        await asyncio.to_thread(build_summary, pairs, out_path)
    except Exception as e:  # noqa: BLE001
        await max_client.send_message(chat_id, f"❌ Ошибка сборки xlsx: {e}")
        return

    try:
        await max_client.send_document(chat_id, str(out_path), caption=f"Сводная за {target}")
    except MaxError as e:
        await max_client.send_message(chat_id, f"❌ Не удалось отправить файл: {e}")


async def run_bot() -> None:
    """Main bot loop. Long polling, graceful shutdown on SIGTERM/SIGINT."""
    s = get_settings()
    if not s.max_bot_token:
        raise RuntimeError("MAX_BOT_TOKEN is not set")
    if not s.yandex_gpt_api_key or not s.yandex_gpt_folder_id:
        raise RuntimeError("YANDEX_GPT_API_KEY / YANDEX_GPT_FOLDER_ID not set")
    if not s.form_published_url:
        raise RuntimeError("FORM_PUBLISHED_URL is not set")

    logging.basicConfig(level=s.log_level, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    max_client = MaxClient(s.max_bot_token)
    llm = YandexGPTClient(
        api_key=s.yandex_gpt_api_key,
        folder_id=s.yandex_gpt_folder_id,
        model=s.yandex_gpt_model,
        max_tokens=s.yandex_gpt_max_tokens,
    )
    form_url = s.form_published_url
    screenshot_dir = s.data_dir / "submissions"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    dao = SubmissionDAO(s.db_full_path)
    disk_client: YandexDiskClient | None = None
    if s.yandex_disk_oauth_token:
        disk_client = YandexDiskClient(
            oauth_token=s.yandex_disk_oauth_token,
            refresh_token=s.yandex_disk_refresh_token,
            client_id=s.yandex_disk_client_id,
            client_secret=s.yandex_disk_client_secret,
        )

    # Real Playwright (lazy import; requires `playwright install chromium` for runtime)
    from backend.forms.playwright_real import RealPlaywrightClient

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    import contextlib
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):  # Windows
            loop.add_signal_handler(sig, stop_event.set)

    pipeline_deps: dict[str, Any] = {
        "llm": llm,
        "form_client": RealPlaywrightClient(
            headless=True, user_data_dir=s.data_dir / "chromium"
        ),
        "disk_client": disk_client,
        "form_url": form_url,
        "screenshot_dir": screenshot_dir,
        "dao": dao,
        "default_foreman": s.default_foreman,
        "data_dir": s.data_dir,
    }

    logger.info("Bot starting (token=%s…)", s.max_bot_token[:8])
    offset: int | None = None
    try:
        while not stop_event.is_set():
            try:
                updates = await max_client.get_updates(
                    offset=offset, timeout=s.max_polling_timeout
                )
            except MaxError as e:
                logger.error("getUpdates failed: %s; sleeping 5s", e)
                await asyncio.sleep(5)
                continue

            for upd in updates:
                offset = upd["update_id"] + 1
                msg = upd.get("message") or {}
                text = msg.get("text", "")
                chat = msg.get("chat", {})
                chat_id = chat.get("id")
                if not chat_id or not text:
                    continue
                # Per-message dependencies: fresh form_client (one form per message)
                pipeline_deps["form_client"] = RealPlaywrightClient(
                    headless=True, user_data_dir=s.data_dir / "chromium"
                )
                try:
                    await handle_message(
                        chat_id, text, max_client=max_client, pipeline_deps=pipeline_deps
                    )
                except Exception as e:  # noqa: BLE001
                    logger.exception("handle_message failed")
                    with contextlib.suppress(Exception):
                        await max_client.send_message(chat_id, f"❌ Ошибка: {e}")
    finally:
        await max_client.close()
        await llm.close()
        if disk_client is not None:
            await disk_client.close()
        logger.info("Bot stopped")
