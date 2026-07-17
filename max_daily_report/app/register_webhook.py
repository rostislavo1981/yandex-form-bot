from __future__ import annotations

import asyncio

from app.config import settings
from app.services.max_client import WEBHOOK_UPDATE_TYPES, MAXClient


async def sync_webhook(
    client: MAXClient,
    webhook_url: str,
    secret: str,
) -> tuple[list[dict], list[str]]:
    """Register the current URL and remove every stale URL for this bot."""
    await client.subscribe_webhook(webhook_url, secret)
    subscriptions = await client.get_subscriptions()
    stale_urls = sorted(
        {
            str(item["url"])
            for item in subscriptions
            if item.get("url") and item.get("url") != webhook_url
        }
    )
    for stale_url in stale_urls:
        await client.delete_webhook_subscription(stale_url)
    if stale_urls:
        subscriptions = await client.get_subscriptions()
    return subscriptions, stale_urls


async def register() -> None:
    if not settings.max_bot_token:
        raise SystemExit("MAX_BOT_TOKEN is empty")
    if not settings.max_webhook_secret:
        raise SystemExit("MAX_WEBHOOK_SECRET is empty")
    if not settings.webapp_public_url.startswith("https://"):
        raise SystemExit("WEBAPP_PUBLIC_URL must start with https://")

    webhook_url = f"{settings.webapp_public_url.rstrip('/')}/api/webhook/max"
    client = MAXClient()
    try:
        bot = await client.get_me()
        subscriptions, removed_urls = await sync_webhook(
            client,
            webhook_url,
            settings.max_webhook_secret,
        )
    finally:
        await client.close()

    username = bot.get("username") or "<not returned>"
    subscription = next(
        (item for item in subscriptions if item.get("url") == webhook_url),
        None,
    )
    registered = subscription is not None
    current_types = set((subscription or {}).get("update_types", []))
    events_ready = set(WEBHOOK_UPDATE_TYPES).issubset(current_types)
    print(f"Bot username: {username}")
    print(f"Webhook URL: {webhook_url}")
    print(f"Webhook visible in subscriptions: {'yes' if registered else 'no'}")
    print(f"Webhook events up to date: {'yes' if events_ready else 'no'}")
    print(f"Removed stale webhook subscriptions: {len(removed_urls)}")


if __name__ == "__main__":
    asyncio.run(register())
