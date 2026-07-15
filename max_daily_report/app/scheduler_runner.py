from __future__ import annotations

import asyncio
import logging
import os
from datetime import date
from typing import Any

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.users import MAXGroup

logger = logging.getLogger("scheduler")
logging.basicConfig(level=getattr(settings, "log_level", "INFO").upper())

API_BASE_URL = os.getenv("SCHEDULER_API_URL", "http://api:8000").rstrip("/")
TIMEZONE = os.getenv("SCHEDULER_TIMEZONE", "Europe/Moscow")


async def _active_group_ids(session) -> list[int]:
    result = await session.execute(
        select(MAXGroup.id).where(MAXGroup.active.is_(True)).order_by(MAXGroup.id)
    )
    return list(result.scalars().all())


async def _api_post(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    headers = {}
    if settings.internal_token:
        headers["X-Internal-Token"] = settings.internal_token
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{API_BASE_URL}{path}", params=params or {}, headers=headers
        )
        response.raise_for_status()
        return response.json()


async def run_morning() -> None:
    logger.info("Running morning obligations")
    try:
        result = await _api_post("/api/scheduler/morning")
        logger.info("Morning obligations result: %s", result)
    except Exception:  # noqa: BLE001
        logger.exception("Morning obligations failed")


async def run_evening_reminder(reminder_number: int) -> None:
    logger.info("Running evening reminder #%s", reminder_number)
    async with AsyncSessionLocal() as session:
        group_ids = await _active_group_ids(session)
    if not group_ids:
        logger.warning("No active groups for evening reminder")
        return

    target = date.today()
    for group_id in group_ids:
        try:
            result = await _api_post(
                "/api/scheduler/evening-reminder",
                params={
                    "group_id": group_id,
                    "reminder_number": reminder_number,
                    "target_date": target.isoformat(),
                },
            )
            logger.info("Evening reminder #%s for group %s: %s", reminder_number, group_id, result)
        except Exception:  # noqa: BLE001
            logger.exception("Evening reminder #%s failed for group %s", reminder_number, group_id)


async def run_morning_summary() -> None:
    logger.info("Running morning summary")
    async with AsyncSessionLocal() as session:
        group_ids = await _active_group_ids(session)
    if not group_ids:
        logger.warning("No active groups for morning summary")
        return

    # summary is for the previous day
    target = date.fromordinal(date.today().toordinal() - 1)
    for group_id in group_ids:
        try:
            result = await _api_post(
                "/api/scheduler/morning-summary",
                params={"group_id": group_id, "target_date": target.isoformat()},
            )
            logger.info("Morning summary for group %s: %s", group_id, result)
        except Exception:  # noqa: BLE001
            logger.exception("Morning summary failed for group %s", group_id)


async def run_outbox() -> None:
    logger.info("Processing outbox")
    try:
        result = await _api_post("/api/worker/process-outbox", params={"limit": 50})
        logger.info("Outbox result: %s", result)
    except Exception:  # noqa: BLE001
        logger.exception("Outbox processing failed")


def build_scheduler() -> AsyncIOScheduler:
    """APScheduler исполняет coroutine-функции сам — без create_task-обёртки,
    иначе задача держится только слабой ссылкой и может быть удалена GC."""
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)

    # create obligations shortly after midnight
    scheduler.add_job(
        run_morning,
        CronTrigger(hour=0, minute=5),
        id="morning_obligations",
        replace_existing=True,
    )

    # evening reminders
    scheduler.add_job(
        run_evening_reminder,
        CronTrigger(hour=20, minute=0),
        args=[1],
        id="evening_reminder_1",
        replace_existing=True,
    )
    scheduler.add_job(
        run_evening_reminder,
        CronTrigger(hour=20, minute=30),
        args=[2],
        id="evening_reminder_2",
        replace_existing=True,
    )

    # morning summary
    scheduler.add_job(
        run_morning_summary,
        CronTrigger(hour=8, minute=0),
        id="morning_summary",
        replace_existing=True,
    )

    # outbox processing — every minute
    scheduler.add_job(
        run_outbox,
        CronTrigger(minute="*"),
        id="outbox_process",
        replace_existing=True,
    )

    return scheduler


async def main() -> None:
    scheduler = build_scheduler()
    scheduler.start()
    logger.info("Scheduler started")
    try:
        while True:
            await asyncio.sleep(3600)
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Scheduler shutting down")
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
