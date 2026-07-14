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


def test_webhook_open_report_uses_max_link_without_token(client: TestClient, monkeypatch):
    """F2.2: ссылка ведёт на max.ru и не содержит фрагментов токена."""
    monkeypatch.setattr(settings, "max_webhook_secret", "secret")
    monkeypatch.setattr(settings, "max_bot_token", "bot123:supersecrettoken")
    monkeypatch.setattr(settings, "max_bot_username", "daily_report_bot")
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
    text = instance.send_message.await_args.kwargs["text"]
    assert "max.ru/daily_report_bot" in text
    assert "t.me" not in text
    assert "bot123" not in text
    assert "supersecrettoken" not in text


def test_webhook_my_reports_lists_user_reports(client: TestClient, monkeypatch, db_session):
    """F2.1: my_reports использует реальные поля модели и не падает."""
    from datetime import date

    from app.models.catalogs import Object, ObjectStage, Stage
    from app.models.reports import DailyReport
    from app.models.users import User

    monkeypatch.setattr(settings, "max_webhook_secret", "secret")

    user = User(max_user_id="max-77", full_name="Reporter", role="responsible")
    obj = Object(code="obj-wh", name="Вебхук-объект", execution_method="own")
    stage = Stage(code="st-wh", name="Этап")
    db_session.add_all([user, obj, stage])
    db_session.flush()
    db_session.add(ObjectStage(object_id=obj.id, stage_id=stage.id))
    db_session.add(
        DailyReport(
            report_date=date(2026, 7, 14),
            responsible_user_id=user.id,
            object_id=obj.id,
            stage_id=stage.id,
            staff_itr=1,
            idempotency_key="wh-key-1",
        )
    )
    db_session.commit()

    event = {
        "type": "callback",
        "callbackData": "my_reports",
        "sender": {"userId": "max-77", "name": "Reporter"},
        "chat": {"chatId": "chat-9"},
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
    text = instance.send_message.await_args.kwargs["text"]
    assert "obj-wh" in text
    assert "2026-07-14" in text


def test_webhook_group_status_handled(client: TestClient, monkeypatch):
    """F2.3: кнопка group_status больше не мёртвая."""
    monkeypatch.setattr(settings, "max_webhook_secret", "secret")
    event = {
        "type": "callback",
        "callbackData": "group_status:1",
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
    assert "Статус" in instance.send_message.await_args.kwargs["text"]


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
