from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_webhook_missing_secret(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "max_webhook_secret", "secret")
    response = client.post("/api/webhook/max", json={"update_type": "bot_started"})
    assert response.status_code == 401


def test_webhook_invalid_secret(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "max_webhook_secret", "secret")
    response = client.post(
        "/api/webhook/max",
        json={"update_type": "bot_started"},
        headers={"x-max-bot-api-secret": "bad"},
    )
    assert response.status_code == 401


def test_webhook_bot_started(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "max_webhook_secret", "secret")
    monkeypatch.setattr(settings, "max_bot_token", "bot123:token")
    event = {
        "update_type": "bot_started",
        "user": {"user_id": "max-42", "name": "Test User"},
        "chat_id": "chat-1",
    }
    with patch("app.api.webhook.MAXClient") as MockClient:
        instance = MockClient.return_value
        instance.send_message = AsyncMock()
        instance.answer_callback = AsyncMock()
        instance.close = AsyncMock()
        response = client.post(
            "/api/webhook/max",
            json=event,
            headers={"x-max-bot-api-secret": "secret"},
        )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    instance.send_message.assert_awaited_once()
    args = instance.send_message.await_args.kwargs
    assert args["chat_id"] == "chat-1"
    instance.close.assert_awaited_once()


def test_webhook_bot_added_activates_group_and_panel(
    client: TestClient, monkeypatch, db_session
):
    from sqlalchemy import select

    from app.models.users import MAXGroup

    monkeypatch.setattr(settings, "max_webhook_secret", "secret")
    event = {
        "update_type": "bot_added",
        "user": {"user_id": "max-admin-1", "name": "Group Admin"},
        "chat_id": "group-777",
        "is_channel": False,
    }
    with (
        patch("app.api.webhook.MAXClient") as MockClient,
        patch(
            "app.api.webhook.ControlPanelService.ensure_group_control_panel",
            new=AsyncMock(return_value={"status": "ok"}),
        ) as ensure_panel,
    ):
        instance = MockClient.return_value
        instance.get_chat = AsyncMock(
            return_value={"chat_id": "group-777", "title": "Тестовая группа"}
        )
        instance.close = AsyncMock()
        response = client.post(
            "/api/webhook/max",
            json=event,
            headers={"x-max-bot-api-secret": "secret"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    group = db_session.execute(
        select(MAXGroup).where(MAXGroup.chat_id == "group-777")
    ).scalar_one()
    assert group.title == "Тестовая группа"
    assert group.active is True
    ensure_panel.assert_awaited_once_with(group.id)


def test_webhook_callback_open_report(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "max_webhook_secret", "secret")
    monkeypatch.setattr(settings, "max_bot_token", "bot123:token")
    event = {
        "update_type": "message_callback",
        "callback": {"payload": "open_report", "callback_id": "cb-1"},
        "user": {"user_id": "max-42", "name": "Test User"},
        "chat_id": "chat-1",
    }
    with patch("app.api.webhook.MAXClient") as MockClient:
        instance = MockClient.return_value
        instance.send_message = AsyncMock()
        instance.answer_callback = AsyncMock()
        instance.close = AsyncMock()
        response = client.post(
            "/api/webhook/max",
            json=event,
            headers={"x-max-bot-api-secret": "secret"},
        )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    instance.send_message.assert_awaited_once()
    instance.answer_callback.assert_awaited_once_with(callback_id="cb-1")
    assert instance.close.await_count == 2


def test_webhook_open_report_uses_max_link_without_token(client: TestClient, monkeypatch):
    """F2.2: ссылка ведёт на max.ru и не содержит фрагментов токена."""
    monkeypatch.setattr(settings, "max_webhook_secret", "secret")
    monkeypatch.setattr(settings, "max_bot_token", "bot123:supersecrettoken")
    monkeypatch.setattr(settings, "max_bot_username", "daily_report_bot")
    event = {
        "update_type": "message_callback",
        "callback": {"payload": "open_report", "callback_id": "cb-1"},
        "user": {"user_id": "max-42", "name": "Test User"},
        "chat_id": "chat-1",
    }
    with patch("app.api.webhook.MAXClient") as MockClient:
        instance = MockClient.return_value
        instance.send_message = AsyncMock()
        instance.answer_callback = AsyncMock()
        instance.close = AsyncMock()
        response = client.post(
            "/api/webhook/max",
            json=event,
            headers={"x-max-bot-api-secret": "secret"},
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
            object_name_snapshot="Вебхук-объект",
            staff_itr=1,
            idempotency_key="wh-key-1",
        )
    )
    db_session.commit()

    event = {
        "update_type": "message_callback",
        "callback": {"payload": "my_reports", "callback_id": "cb-2"},
        "user": {"user_id": "max-77", "name": "Reporter"},
        "chat_id": "chat-9",
    }
    with patch("app.api.webhook.MAXClient") as MockClient:
        instance = MockClient.return_value
        instance.send_message = AsyncMock()
        instance.answer_callback = AsyncMock()
        instance.close = AsyncMock()
        response = client.post(
            "/api/webhook/max",
            json=event,
            headers={"x-max-bot-api-secret": "secret"},
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
        "update_type": "message_callback",
        "callback": {"payload": "group_status:1", "callback_id": "cb-3"},
        "user": {"user_id": "max-42", "name": "Test User"},
        "chat_id": "chat-1",
    }
    with patch("app.api.webhook.MAXClient") as MockClient:
        instance = MockClient.return_value
        instance.send_message = AsyncMock()
        instance.answer_callback = AsyncMock()
        instance.close = AsyncMock()
        response = client.post(
            "/api/webhook/max",
            json=event,
            headers={"x-max-bot-api-secret": "secret"},
        )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "Статус" in instance.send_message.await_args.kwargs["text"]


def test_webhook_unknown_event(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "max_webhook_secret", "secret")
    event = {"update_type": "unknown"}
    response = client.post(
        "/api/webhook/max",
        json=event,
        headers={"x-max-bot-api-secret": "secret"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"


def test_webhook_help(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "max_webhook_secret", "secret")
    event = {
        "update_type": "message_callback",
        "callback": {"payload": "help", "callback_id": "cb-help"},
        "user": {"user_id": "max-42", "name": "Test User"},
        "chat_id": "chat-1",
    }
    with patch("app.api.webhook.MAXClient") as MockClient:
        instance = MockClient.return_value
        instance.send_message = AsyncMock()
        instance.answer_callback = AsyncMock()
        instance.close = AsyncMock()
        response = client.post(
            "/api/webhook/max",
            json=event,
            headers={"x-max-bot-api-secret": "secret"},
        )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    text = instance.send_message.await_args.kwargs["text"]
    assert "Помощь" in text


def test_webhook_group_missing(client: TestClient, monkeypatch, db_session):
    monkeypatch.setattr(settings, "max_webhook_secret", "secret")
    from datetime import date

    from app.models.catalogs import Object, ObjectStage, Stage
    from app.models.reports import ReportObligation, ResponsibleObjectAssignment
    from app.models.users import User

    user = User(max_user_id="max-miss", full_name="Missing User", role="responsible")
    obj = Object(code="obj-miss", name="Missing Obj", execution_method="own")
    stage = Stage(code="st-miss", name="Stage")
    db_session.add_all([user, obj, stage])
    db_session.flush()
    db_session.add(ObjectStage(object_id=obj.id, stage_id=stage.id))
    assignment = ResponsibleObjectAssignment(
        user_id=user.id, object_id=obj.id,
        active_from=date(2026, 1, 1), active_to=date(2026, 12, 31),
        schedule_type="daily",
    )
    db_session.add(assignment)
    db_session.flush()
    db_session.add(
        ReportObligation(
            report_date=date.today(),
            assignment_id=assignment.id,
            user_id=user.id,
            object_id=obj.id,
            status="pending",
        )
    )
    db_session.commit()

    event = {
        "update_type": "message_callback",
        "callback": {"payload": "group_missing:1", "callback_id": "cb-miss"},
        "user": {"user_id": "max-42", "name": "Admin"},
        "chat_id": "chat-1",
    }
    with patch("app.api.webhook.MAXClient") as MockClient:
        instance = MockClient.return_value
        instance.send_message = AsyncMock()
        instance.answer_callback = AsyncMock()
        instance.close = AsyncMock()
        response = client.post(
            "/api/webhook/max",
            json=event,
            headers={"x-max-bot-api-secret": "secret"},
        )
    assert response.status_code == 200
    text = instance.send_message.await_args.kwargs["text"]
    assert "Missing User" in text
