from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import create_app
from app.models.users import User


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture(autouse=True)
def _dev_env(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "dev")
    monkeypatch.setattr(settings, "debug", True)


def _insert_user(db_session, role: str) -> User:
    user = User(max_user_id="dev-user", full_name="Dev User", role=role)
    db_session.add(user)
    db_session.commit()
    return user


def test_ensure_group_panel_requires_auth(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "debug", False)
    response = client.post("/api/control-panel/group/1/ensure")
    assert response.status_code == 401


def test_ensure_group_panel_requires_manager(client: TestClient, db_session):
    _insert_user(db_session, "responsible")
    response = client.post("/api/control-panel/group/1/ensure")
    assert response.status_code == 403


def test_ensure_group_panel_manager(client: TestClient, db_session, monkeypatch):
    _insert_user(db_session, "manager")
    with patch("app.api.control_panel.ControlPanelService") as MockService:
        instance = MockService.return_value
        instance.ensure_group_control_panel = AsyncMock(
            return_value={"status": "ok", "message_id": "msg-1"}
        )
        response = client.post("/api/control-panel/group/1/ensure")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    instance.ensure_group_control_panel.assert_awaited_once_with(1)


def test_ensure_private_panel_requires_auth(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "debug", False)
    response = client.post("/api/control-panel/private/ensure")
    assert response.status_code == 401


def test_refresh_group_panel_schedules_outbox(client: TestClient, db_session):
    _insert_user(db_session, "manager")
    with patch("app.api.control_panel.ControlPanelService") as MockService:
        instance = MockService.return_value
        instance.refresh_group_panel_outbox = AsyncMock()
        response = client.post("/api/control-panel/group/1/refresh")
    assert response.status_code == 200
    assert response.json()["status"] == "scheduled"
    args, _ = instance.refresh_group_panel_outbox.await_args
    assert args[0] == 1
