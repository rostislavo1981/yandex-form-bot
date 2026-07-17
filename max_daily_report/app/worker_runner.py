from __future__ import annotations

import asyncio
import logging
import os

import httpx

from app.config import settings

logger = logging.getLogger("worker")
logging.basicConfig(level=getattr(settings, "log_level", "INFO").upper())

API_BASE_URL = os.getenv("WORKER_API_URL", "http://api:8000").rstrip("/")
POLL_SECONDS = max(1.0, float(os.getenv("WORKER_POLL_SECONDS", "2")))


async def process_once() -> dict[str, int]:
    headers = {}
    if settings.internal_token:
        headers["X-Internal-Token"] = settings.internal_token
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{API_BASE_URL}/api/worker/process-outbox",
            params={"limit": 50},
            headers=headers,
        )
        response.raise_for_status()
        return response.json()


async def main() -> None:
    logger.info("Outbox worker started; poll interval %.1fs", POLL_SECONDS)
    while True:
        try:
            result = await process_once()
            if result.get("success") or result.get("failed"):
                logger.info("Outbox result: %s", result)
        except Exception:  # noqa: BLE001
            logger.exception("Outbox processing failed")
        await asyncio.sleep(POLL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
