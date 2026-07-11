"""Tests for /webapp command + send_webapp_button."""
from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from backend.max import MaxClient
from backend.max.bot import handle_message
from backend.max.commands import send_webapp_button


class FakeLLM:
    async def complete(self, *a: Any, **k: Any) -> str:
        return json.dumps(
            {
                "date": "2026-07-10",
                "foreman": "X",
                "object_name": "Y",
                "machines": [],
                "personnel": {"itr": 0, "opr_staff": 0, "opr_external": 0},
                "waste_volume": 0,
            },
            ensure_ascii=False,
        )


def _client_with(handler: Callable[[httpx.Request], httpx.Response]) -> MaxClient:
    c = MaxClient(token="t", base_url="https://bot.test")
    c._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return c


@pytest.mark.asyncio
async def test_send_webapp_button_with_button(monkeypatch: pytest.MonkeyPatch) -> None:
    """If sendMessage supports reply_markup, button is attached."""
    monkeypatch.setenv("WEBAPP_PUBLIC_URL", "https://bot.example.com")

    sent: list = []

    async def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content.decode())
        sent.append(body)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    c = _client_with(handler)
    try:
        await send_webapp_button(c, 42, date_to="2026-07-10")
    finally:
        await c.close()
    # reply_markup contains inline_keyboard with web_app
    body = sent[0]
    assert "reply_markup" in body
    btn = body["reply_markup"]["inline_keyboard"][0][0]
    assert "web_app" in btn
    assert "date_to=2026-07-10" in btn["web_app"]["url"]


@pytest.mark.asyncio
async def test_send_webapp_button_fallback_on_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If reply_markup not accepted, falls back to plain text URL."""
    monkeypatch.setenv("WEBAPP_PUBLIC_URL", "https://bot.example.com")

    sent: list = []

    async def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content.decode())
        sent.append(body)
        if "reply_markup" in body:
            return httpx.Response(200, json={"ok": False, "description": "web_app not supported"})
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    c = _client_with(handler)
    try:
        await send_webapp_button(c, 42)
    finally:
        await c.close()
    # 2 calls: 1 failed, 1 plain
    assert len(sent) == 2
    assert "https://bot.example.com" in sent[1]["text"]


@pytest.mark.asyncio
async def test_handle_webapp_command(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bot /webapp → message with webapp button."""
    monkeypatch.setenv("WEBAPP_PUBLIC_URL", "https://bot.example.com")

    sent: list = []

    async def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content.decode())
        sent.append(body)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    from backend.db import SubmissionDAO
    from backend.forms import FakePlaywrightClient

    c = _client_with(handler)
    pipeline_deps = {
        "llm": FakeLLM(),
        "form_client": FakePlaywrightClient(),
        "disk_client": None,
        "form_url": "https://forms.yandex.ru/x",
        "screenshot_dir": __import__("pathlib").Path("/tmp"),
        "dao": SubmissionDAO(__import__("pathlib").Path("/tmp/test.db")),
        "default_foreman": "X",
        "data_dir": __import__("pathlib").Path("/tmp"),
    }
    try:
        await handle_message(42, "/webapp", max_client=c, pipeline_deps=pipeline_deps)
    finally:
        await c.close()
    assert any("web_app" in str(s) for s in sent)
