from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def _signature(payload: bytes) -> str:
    return hmac.new(settings.max_webhook_secret.encode(), payload, hashlib.sha256).hexdigest()


def test_webhook_missing_signature(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "max_webhook_secret", "secret")
    response = client.post("/api/webhook/max", json={"type": "bot_started"})
    assert response.status_code == 401


def test_webhook_invalid_signature(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "max_webhook_secret", "secret")
    response = client.post(
        "/api/webhook/max",
        json={"type": "bot_started"},
        headers={"x-signature": "bad"},
    )
    assert response.status_code == 401


def test_webhook_bot_started(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "max_webhook_secret", "secret")
    monkeypatch.setattr(settings, "max_bot_token", "bot123:token")
    event = {
        "type": "bot_started",
        "sender": {"userId": "max-42", "name": "Test User"},
        "chat": {"chatId": "chat-1"},
    }
    payload = json.dumps(event).encode()
    with patch("app.api.webhook.MAXClient") as MockClient:
        instance = MockClient.return_value
        instance.send_message = AsyncMock()
        instance.close = AsyncMock()
        response = client.post(
            "/api/webhook/max",
            content=payload,
            headers={"x-signature": _signature(payload), "content-type": "application/json"},
        )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    instance.send_message.assert_awaited_once()
    args = instance.send_message.await_args.kwargs
    assert args["chat_id"] == "chat-1"
    instance.close.assert_awaited_once()


def test_webhook_callback_open_report(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "max_webhook_secret", "secret")
    monkeypatch.setattr(settings, "max_bot_token", "bot123:token")
    event = {
        "type": "callback",
        "callbackData": "open_report",
        "sender": {"userId": "max-42", "name": "Test User"},
        "chat": {"chatId": "chat-1"},
    }
    payload = json.dumps(event).encode()
    with patch("app.api.webhook.MAXClient") as MockClient:
        instance = MockClient.return_value
        instance.send_message = AsyncMock()
        instance.close = AsyncMock()
        response = client.post(
            "/api/webhook/max",
            content=payload,
            headers={"x-signature": _signature(payload), "content-type": "application/json"},
        )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    instance.send_message.assert_awaited_once()
    instance.close.assert_awaited_once()


def test_webhook_unknown_event(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "max_webhook_secret", "secret")
    event = {"type": "unknown"}
    payload = json.dumps(event).encode()
    response = client.post(
        "/api/webhook/max",
        content=payload,
        headers={"x-signature": _signature(payload), "content-type": "application/json"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
