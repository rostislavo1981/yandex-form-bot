from __future__ import annotations

import json

import httpx
import pytest

from app.services.max_client import MAXClient, _extract_message_id, _headers, _keyboard_attachment


def _mock_client(handler):
    client = MAXClient(base_url="https://bot.test")
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return client


class TestExtractMessageId:
    def test_extracts_official_nested_message_id(self):
        assert _extract_message_id({"message": {"body": {"mid": "official-123"}}}) == "official-123"

    def test_extracts_message_id(self):
        assert _extract_message_id({"message_id": "123"}) == "123"

    def test_extracts_msg_id(self):
        assert _extract_message_id({"msgId": "456"}) == "456"

    def test_extracts_message_id_camel(self):
        assert _extract_message_id({"messageId": "789"}) == "789"

    def test_returns_empty_string_on_missing(self):
        assert _extract_message_id({}) == ""

    def test_returns_empty_string_on_none(self):
        assert _extract_message_id({"message_id": None}) == ""


class TestKeyboardAttachment:
    def test_converts_callback_buttons(self):
        rows = [[{"text": "Click", "callback_data": "action"}]]
        result = _keyboard_attachment(rows)
        assert result["type"] == "inline_keyboard"
        assert result["payload"]["buttons"][0][0]["type"] == "callback"
        assert result["payload"]["buttons"][0][0]["payload"] == "action"

    def test_preserves_non_callback_buttons(self):
        button = {"type": "open_app", "text": "Open", "url": "https://example.com"}
        rows = [[button]]
        result = _keyboard_attachment(rows)
        assert result["payload"]["buttons"][0][0] == button


class TestHeaders:
    def test_contains_authorization(self):
        h = _headers()
        assert "Authorization" in h
        assert "Content-Type" in h


@pytest.mark.asyncio
async def test_send_message_uses_query_params():
    captured: dict = {}

    async def handler(req: httpx.Request) -> httpx.Response:
        captured["url"] = str(req.url)
        captured["params"] = dict(req.url.params)
        body = req.content.decode()
        captured["body"] = body
        return httpx.Response(200, json={"message": {"body": {"mid": "999"}}})

    client = _mock_client(handler)
    try:
        result = await client.send_message(chat_id="42", text="Hello")
    finally:
        await client.close()

    assert "chat_id=42" in captured["url"]
    assert "Hello" in captured["body"]
    assert "chatId" not in captured["body"]
    assert result["message_id"] == "999"


@pytest.mark.asyncio
async def test_edit_message_uses_query_params():
    captured: dict = {}

    async def handler(req: httpx.Request) -> httpx.Response:
        captured["url"] = str(req.url)
        captured["body"] = req.content.decode()
        return httpx.Response(200, json={})

    client = _mock_client(handler)
    try:
        await client.edit_message(chat_id="42", message_id="100", text="Updated")
    finally:
        await client.close()

    assert "chat_id" not in captured["url"]
    assert "message_id=100" in captured["url"]
    assert "Updated" in captured["body"]
    assert "chatId" not in captured["body"]
    assert "msgId" not in captured["body"]


@pytest.mark.asyncio
async def test_pin_message_uses_query_params():
    captured: dict = {}

    async def handler(req: httpx.Request) -> httpx.Response:
        captured["url"] = str(req.url)
        captured["body"] = req.content.decode()
        return httpx.Response(200, json={})

    client = _mock_client(handler)
    try:
        await client.pin_message(chat_id="42", message_id="100")
    finally:
        await client.close()

    assert "chats/42/pin" in captured["url"]
    assert "message_id" not in captured["url"]
    body = json.loads(captured["body"])
    assert body == {"message_id": "100", "notify": True}


@pytest.mark.asyncio
async def test_answer_callback():
    captured: dict = {}

    async def handler(req: httpx.Request) -> httpx.Response:
        captured["url"] = str(req.url)
        captured["body"] = req.content.decode()
        return httpx.Response(200, json={})

    client = _mock_client(handler)
    try:
        await client.answer_callback(callback_id="cb123", text="Done", show_alert=True)
    finally:
        await client.close()

    assert "/answers" in captured["url"]
    assert "callback_id=cb123" in captured["url"]
    body = json.loads(captured["body"])
    assert body == {"notification": "Done"}


@pytest.mark.asyncio
async def test_send_message_keyboard_format():
    captured: dict = {}

    async def handler(req: httpx.Request) -> httpx.Response:
        captured["body"] = req.content.decode()
        return httpx.Response(200, json={"message_id": "1"})

    client = _mock_client(handler)
    try:
        await client.send_message(
            chat_id="42",
            text="Test",
            inline_keyboard=[[{"text": "Click", "callback_data": "act"}]],
        )
    finally:
        await client.close()

    body = json.loads(captured["body"])
    assert body["attachments"][0]["type"] == "inline_keyboard"
    assert body["attachments"][0]["payload"]["buttons"][0][0]["type"] == "callback"
    assert body["attachments"][0]["payload"]["buttons"][0][0]["payload"] == "act"


@pytest.mark.asyncio
async def test_subscribe_webhook_includes_group_lifecycle_events():
    captured: dict = {}

    async def handler(req: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(req.content.decode())
        return httpx.Response(200, json={"success": True})

    client = _mock_client(handler)
    try:
        await client.subscribe_webhook("https://example.com/hook", "secret-value")
    finally:
        await client.close()

    assert set(captured["body"]["update_types"]) == {
        "bot_added",
        "bot_removed",
        "bot_started",
        "message_callback",
    }


@pytest.mark.asyncio
async def test_delete_webhook_subscription_uses_exact_url_query_param():
    captured: dict = {}

    async def handler(req: httpx.Request) -> httpx.Response:
        captured["method"] = req.method
        captured["path"] = req.url.path
        captured["params"] = dict(req.url.params)
        return httpx.Response(200, json={"success": True})

    client = _mock_client(handler)
    try:
        result = await client.delete_webhook_subscription(
            "https://old.example.com/api/webhook/max"
        )
    finally:
        await client.close()

    assert captured == {
        "method": "DELETE",
        "path": "/subscriptions",
        "params": {"url": "https://old.example.com/api/webhook/max"},
    }
    assert result == {"success": True}
