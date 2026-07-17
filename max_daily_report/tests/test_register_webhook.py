from __future__ import annotations

import pytest

from app.register_webhook import sync_webhook


class FakeMAXClient:
    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.subscriptions = [
            {"url": "https://old-b.example/api/webhook/max"},
            {"url": "https://current.example/api/webhook/max"},
            {"url": "https://old-a.example/api/webhook/max"},
            {"url": "https://old-a.example/api/webhook/max"},
        ]

    async def subscribe_webhook(self, url: str, secret: str) -> dict:
        self.calls.append(("subscribe", url, secret))
        return {"success": True}

    async def get_subscriptions(self) -> list[dict]:
        self.calls.append(("get",))
        return list(self.subscriptions)

    async def delete_webhook_subscription(self, url: str) -> dict:
        self.calls.append(("delete", url))
        self.subscriptions = [
            item for item in self.subscriptions if item.get("url") != url
        ]
        return {"success": True}


@pytest.mark.asyncio
async def test_sync_webhook_registers_current_then_removes_stale_urls():
    client = FakeMAXClient()

    subscriptions, removed = await sync_webhook(
        client,  # type: ignore[arg-type]
        "https://current.example/api/webhook/max",
        "secret",
    )

    assert removed == [
        "https://old-a.example/api/webhook/max",
        "https://old-b.example/api/webhook/max",
    ]
    assert subscriptions == [
        {"url": "https://current.example/api/webhook/max"}
    ]
    assert client.calls == [
        ("subscribe", "https://current.example/api/webhook/max", "secret"),
        ("get",),
        ("delete", "https://old-a.example/api/webhook/max"),
        ("delete", "https://old-b.example/api/webhook/max"),
        ("get",),
    ]
