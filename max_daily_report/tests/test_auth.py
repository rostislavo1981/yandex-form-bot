from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database import AsyncSessionLocal
from app.main import app
from app.models.users import User

client = TestClient(app)


def _make_init_data(user_id: int, auth_date: int | None = None, token: str = "test-token") -> str:
    now = auth_date or int(time.time())
    raw_user = f'{{"id":{user_id},"first_name":"Test"}}'
    pairs = {"auth_date": str(now), "user": raw_user}
    launch_params = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(
        b"WebAppData", token.encode(), hashlib.sha256
    ).digest()
    hash_value = hmac.new(secret, launch_params.encode(), hashlib.sha256).hexdigest()
    return f"auth_date={now}&user={quote(raw_user)}&hash={hash_value}"


@pytest.mark.asyncio
async def test_auth_me_dev_header():
    response = client.get("/api/auth/me", headers={"X-Init-Data": "dev"})
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["max_user_id"] == "dev-user"


@pytest.mark.asyncio
async def test_auth_me_rejects_invalid_signature(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "max_bot_token", "test-token")
    response = client.get("/api/auth/me", headers={"X-Init-Data": "user=1&hash=bad"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_me_accepts_valid_signature(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "max_bot_token", "test-token")
    async with AsyncSessionLocal() as session:
        user = User(max_user_id="123", full_name="Real", role="responsible")
        session.add(user)
        await session.commit()

    init_data = _make_init_data(123)
    response = client.get("/api/auth/me", headers={"X-Init-Data": init_data})
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["max_user_id"] == "123"


@pytest.mark.asyncio
async def test_auth_me_rejects_expired_init_data(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "max_bot_token", "test-token")
    init_data = _make_init_data(123, auth_date=int(time.time()) - 7200)
    response = client.get("/api/auth/me", headers={"X-Init-Data": init_data})
    assert response.status_code == 401
