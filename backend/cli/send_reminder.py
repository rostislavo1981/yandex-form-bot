"""Send a daily reminder to foremen at 20:00 to fill the form.

Used by cron (or launchd on macOS dev). Single self-contained run:
no DB state, no loop. Sends the reminder to one or more chat_ids
read from .env (REMINDER_CHAT_IDS=123,456,789) or from
`data/subscribers.json` (a dict of chat_id -> display_name).

Config (via .env, all optional):
  REMINDER_TEXT          text body of the message
  REMINDER_CHAT_IDS      comma-separated list of numeric chat IDs (legacy)
  SUBSCRIBERS_FILE       path to JSON; default: data/subscribers.json
  MAX_BOT_TOKEN          required (read from env)
  FORM_PUBLISHED_URL     included in reminder if set
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from backend.config import get_settings
from backend.max import MaxClient, MaxError

logger = logging.getLogger("reminder")

DEFAULT_TEXT = (
    "⏰ 20:00 — время заполнить ежедневный отчёт по технике, механизмам и персоналу.\n"
    "Заполни сегодня, не откладывай на завтра.\n"
    "📝 Форма: {form_url}"
)


def _load_subscribers(settings) -> list[str]:
    """Resolve the list of chat_ids to send the reminder to."""
    raw = os.getenv("REMINDER_CHAT_IDS", "").strip()
    ids: list[str] = []
    if raw:
        ids = [s.strip() for s in raw.split(",") if s.strip()]

    subs_file = Path(os.getenv("SUBSCRIBERS_FILE", str(settings.data_dir / "subscribers.json")))
    if subs_file.exists():
        try:
            data = json.loads(subs_file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                ids.extend(str(k) for k in data)
            elif isinstance(data, list):
                ids.extend(str(x) for x in data)
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to read %s: %s", subs_file, e)

    # de-dup, preserve order
    seen: set[str] = set()
    out: list[str] = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


async def _send_all(text: str, chat_ids: list[str], token: str) -> tuple[int, int]:
    ok = 0
    fail = 0
    client = MaxClient(token)
    try:
        for cid in chat_ids:
            try:
                await client.send_message(cid, text)
                ok += 1
                logger.info("Reminder sent to %s", cid)
            except MaxError as e:
                fail += 1
                logger.error("Failed to send reminder to %s: %s", cid, e)
    finally:
        await client.close()
    return ok, fail


def main() -> int:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    settings = get_settings()
    token = settings.max_bot_token
    if not token:
        logger.error("MAX_BOT_TOKEN is not set")
        return 2

    chat_ids = _load_subscribers(settings)
    if not chat_ids:
        logger.warning(
            "No subscribers configured. Set REMINDER_CHAT_IDS=1,2,3 in .env "
            "or create data/subscribers.json"
        )
        return 0

    template = os.getenv("REMINDER_TEXT", DEFAULT_TEXT)
    form_url = settings.form_published_url or os.getenv("FORM_PUBLISHED_URL", "")
    text = template.format(form_url=form_url or "(ссылка не настроена)")

    ok, fail = asyncio.run(_send_all(text, chat_ids, token))
    logger.info("Reminder delivered: ok=%d fail=%d (total=%d)", ok, fail, len(chat_ids))
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
