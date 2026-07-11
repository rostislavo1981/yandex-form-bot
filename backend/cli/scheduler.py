"""In-process scheduler that triggers yfb-reminder at a fixed time every day.

Runs as a long-lived container (see `reminder` service in docker-compose.yml).
Sleeps until next target time, fires the reminder, repeats.

Why not system cron inside the container?
- Avoids extra packages (cron, crond)
- One fewer moving part to break
- Logs and exit codes flow through stdout / Docker

Config (env, all optional):
  REMINDER_HOUR     hour to fire (0-23), default 20
  REMINDER_MINUTE   minute to fire (0-59), default 0
  TZ                timezone name, default Europe/Moscow (set in Dockerfile)

On SIGTERM/SIGINT: finish the current sleep and exit cleanly.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import signal
import sys
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from backend.cli.send_reminder import main as run_reminder_main

logger = logging.getLogger("scheduler")


def _now_in_tz() -> datetime:
    tz_name = os.getenv("TZ", "Europe/Moscow")
    try:
        tz = ZoneInfo(tz_name)
    except Exception:  # noqa: BLE001
        logger.warning("Unknown TZ %r, falling back to UTC", tz_name)
        tz = UTC
    return datetime.now(tz)


def _next_fire(now: datetime, hour: int, minute: int) -> datetime:
    """Return the next datetime >= now that hits (hour, minute) in the same tz."""
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


async def _sleep_until(target: datetime, stop_event: asyncio.Event) -> None:
    """Sleep until `target`, but wake up early on `stop_event`."""
    now = _now_in_tz()
    seconds = max(0.0, (target - now).total_seconds())
    logger.info(
        "Next reminder at %s (in %.0f s, %.1f h)",
        target.isoformat(timespec="seconds"),
        seconds,
        seconds / 3600,
    )
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=seconds)
        logger.info("Stop signal received during sleep — exiting")
    except TimeoutError:
        # Normal: slept through to the target time.
        pass


async def _run_scheduler() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    try:
        hour = int(os.getenv("REMINDER_HOUR", "20"))
        minute = int(os.getenv("REMINDER_MINUTE", "0"))
    except ValueError:
        logger.error("REMINDER_HOUR / REMINDER_MINUTE must be integers")
        sys.exit(2)

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        logger.error("REMINDER_HOUR / REMINDER_MINUTE out of range")
        sys.exit(2)

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop_event.set)

    logger.info("Scheduler started. Target: %02d:%02d daily (tz=%s)", hour, minute, os.getenv("TZ", "Europe/Moscow"))

    while not stop_event.is_set():
        now = _now_in_tz()
        target = _next_fire(now, hour, minute)
        await _sleep_until(target, stop_event)
        if stop_event.is_set():
            break
        logger.info("Firing reminder")
        # run_reminder.main() is sync; offload to a thread so we don't block the loop.
        try:
            rc = await asyncio.to_thread(run_reminder_main)
            logger.info("Reminder exited with code %d", rc)
        except Exception as e:  # noqa: BLE001
            logger.exception("Reminder crashed: %s", e)
            # Sleep a bit before retrying so we don't tight-loop on persistent errors
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop_event.wait(), timeout=60)

    logger.info("Scheduler stopped")


def main() -> int:
    try:
        asyncio.run(_run_scheduler())
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
