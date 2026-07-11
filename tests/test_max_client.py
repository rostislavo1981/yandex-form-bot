"""Tests for backend.max.MaxClient (MockTransport)."""
from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest

from backend.max import MaxClient, MaxError


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> MaxClient:
    c = MaxClient(token="test-token", base_url="https://bot.test")
    c._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return c


@pytest.mark.asyncio
async def test_get_updates_returns_list() -> None:
    async def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True, "result": [
            {"update_id": 1, "message": {"message_id": 100, "chat": {"id": 42}, "text": "hi"}},
        ]})

    c = _client(handler)
    try:
        updates = await c.get_updates(offset=0)
    finally:
        await c.close()
    assert len(updates) == 1
    assert updates[0]["message"]["text"] == "hi"


@pytest.mark.asyncio
async def test_get_updates_empty_list() -> None:
    async def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True, "result": []})

    c = _client(handler)
    try:
        updates = await c.get_updates()
    finally:
        await c.close()
    assert updates == []


@pytest.mark.asyncio
async def test_send_message_ok() -> None:
    async def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 999}})

    c = _client(handler)
    try:
        r = await c.send_message(42, "✅ Отправлено")
    finally:
        await c.close()
    assert r["result"]["message_id"] == 999


@pytest.mark.asyncio
async def test_send_message_truncates_long_text() -> None:
    captured: dict = {}

    async def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content.decode())
        captured["text"] = body["text"]
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    c = _client(handler)
    try:
        await c.send_message(42, "x" * 5000)
    finally:
        await c.close()
    assert len(captured["text"]) <= 4000
    assert captured["text"].endswith("...")


@pytest.mark.asyncio
async def test_send_message_api_error() -> None:
    async def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": False, "description": "chat not found"})

    c = _client(handler)
    try:
        with pytest.raises(MaxError, match="chat not found"):
            await c.send_message(42, "x")
    finally:
        await c.close()


@pytest.mark.asyncio
async def test_send_document(tmp_path: object) -> None:
    import tempfile
    from pathlib import Path

    async def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        f.write(b"fake xlsx content")
        path = f.name
    try:
        c = _client(handler)
        try:
            r = await c.send_document(42, path)
        finally:
            await c.close()
        assert r["result"]["message_id"] == 1
    finally:
        Path(path).unlink(missing_ok=True)


def test_constructor_validates_token() -> None:
    with pytest.raises(ValueError, match="token"):
        MaxClient(token="")
