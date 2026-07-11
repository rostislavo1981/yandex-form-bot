"""Tests for backend.max.bot.handle_message and summary command."""
from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from backend.db import SubmissionDAO
from backend.forms import FakePlaywrightClient
from backend.llm import build_user_prompt  # noqa: F401
from backend.max import MaxClient
from backend.max.bot import _handle_summary, handle_message

VALID_REPORT_JSON = json.dumps(
    {
        "date": "2026-07-10",
        "object_name": "РП-7",
        "foreman": "Степанов",
        "works": [{"name": "Копка", "volume": 50.0, "unit": "м", "people_count": 4}],
        "materials": [],
        "notes": None,
        "weather": None,
    },
    ensure_ascii=False,
)


class FakeLLM:
    async def complete(self, user_text: str, system_text: str | None = None) -> str:
        return VALID_REPORT_JSON


def _max_with_handler(handler: Callable[[httpx.Request], httpx.Response]) -> MaxClient:
    c = MaxClient(token="t", base_url="https://bot.test")
    c._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return c


@pytest.mark.asyncio
async def test_handle_help(tmp_path: Path) -> None:
    sent: list = []

    async def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content.decode())
        if "sendMessage" in req.url.path:
            sent.append({"method": "sendMessage", "chat_id": body["chat_id"], "text": body["text"]})
            return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})
        return httpx.Response(200, json={"ok": True, "result": []})

    max_client = _max_with_handler(handler)
    try:
        await handle_message(
            42, "/help", max_client=max_client, pipeline_deps={}
        )
    finally:
        await max_client.close()
    assert any("Яндекс Формы Бот" in s["text"] for s in sent)


@pytest.mark.asyncio
async def test_handle_report_runs_pipeline(tmp_path: Path) -> None:
    sent: list[dict] = []

    async def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content.decode())
        sent.append({"path": req.url.path, "body": body})
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})
    sent: list = []
    max_client = _max_with_handler(handler)
    fake = FakePlaywrightClient()
    dao = SubmissionDAO(tmp_path / "app.db")
    pipeline_deps = {
        "llm": FakeLLM(),
        "form_client": fake,
        "disk_client": None,
        "form_url": "https://forms.yandex.ru/x",
        "screenshot_dir": tmp_path / "submissions",
        "dao": dao,
        "default_foreman": "Степанов",
    }
    try:
        await handle_message(42, "10.07 РП-7 Степанов Копка 50 м", max_client=max_client, pipeline_deps=pipeline_deps)
    finally:
        await max_client.close()
    # 2 messages: "⏳ Парсю…" + "✅ Отправлено"
    assert any("Отправлено" in s["body"]["text"] for s in sent)


@pytest.mark.asyncio
async def test_handle_summary_no_data(tmp_path: Path) -> None:
    sent: list = []

    async def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content.decode())
        sent.append({"path": req.url.path, "text": body.get("text", "")})
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    max_client = _max_with_handler(handler)
    dao = SubmissionDAO(tmp_path / "app.db")
    try:
        await _handle_summary(
            42, "/summary 2026-07-10", max_client=max_client, dao=dao, data_dir=tmp_path
        )
    finally:
        await max_client.close()
    assert any("нет" in s["text"] for s in sent)


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_handle_summary_with_data_sends_file(tmp_path: Path) -> None:
    sent_paths: list[str] = []
    file_received = False

    async def handler(req: httpx.Request) -> httpx.Response:
        nonlocal file_received
        sent_paths.append(req.url.path)
        # sendDocument sends multipart, do not decode the body
        if "sendDocument" in req.url.path:
            # Check that the file was attached (content-type starts with multipart)
            ct = req.headers.get("content-type", "")
            if "multipart" in ct:
                file_received = True
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    dao = SubmissionDAO(tmp_path / "app.db")
    dao.insert(
        foreman="Степанов",
        date="2026-07-10",
        object_name="РП-7",
        report=json.loads(VALID_REPORT_JSON),
    )
    max_client = _max_with_handler(handler)
    try:
        await _handle_summary(
            42, "/summary 2026-07-10", max_client=max_client, dao=dao, data_dir=tmp_path
        )
    finally:
        await max_client.close()
    # sendDocument path used + multipart body
    assert any("sendDocument" in s for s in sent_paths)
    assert file_received, "xlsx file was not attached as multipart"
    out = tmp_path / "summary_2026-07-10.xlsx"
    assert out.exists()


@pytest.mark.asyncio
async def test_handle_summary_invalid_date(tmp_path: Path) -> None:
    sent: list = []

    async def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content.decode())
        sent.append({"text": body.get("text", "")})
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    max_client = _max_with_handler(handler)
    dao = SubmissionDAO(tmp_path / "app.db")
    try:
        await _handle_summary(42, "/summary не дата", max_client=max_client, dao=dao, data_dir=tmp_path)
    finally:
        await max_client.close()
    assert any("Неверная дата" in s["text"] for s in sent)
