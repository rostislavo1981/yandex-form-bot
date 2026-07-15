"""F6 regression tests: initData decode, manager substitution, keyboard format."""
from __future__ import annotations

import hashlib
import hmac
import time
from datetime import date
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database import AsyncSessionLocal
from app.main import app
from app.models.catalogs import Object, ObjectStage, Stage
from app.models.reports import ResponsibleObjectAssignment
from app.models.users import User

client = TestClient(app)


def _make_init_data(raw_user: str, token: str = "test-token") -> str:
    now = int(time.time())
    pairs = {"auth_date": str(now), "user": raw_user}
    launch_params = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    hash_value = hmac.new(secret, launch_params.encode(), hashlib.sha256).hexdigest()
    return f"auth_date={now}&user={quote(raw_user)}&hash={hash_value}"


@pytest.mark.asyncio
async def test_init_data_with_percent_sequences_validates(monkeypatch):
    """F6.2: значение с %-последовательностью не декодируется дважды."""
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "max_bot_token", "test-token")

    async with AsyncSessionLocal() as session:
        session.add(User(max_user_id="777", full_name="Percent", role="responsible"))
        await session.commit()

    # first_name содержит literal "%2B": двойной unquote превратил бы его в "+"
    raw_user = '{"id":777,"first_name":"a%2Bb"}'
    response = client.get(
        "/api/auth/me", headers={"X-Init-Data": _make_init_data(raw_user)}
    )
    assert response.status_code == 200
    assert response.json()["user"]["max_user_id"] == "777"


@pytest.mark.asyncio
async def test_init_data_without_user_id_rejected(monkeypatch):
    """F6.1: user без id — 401, а не поиск пользователя 'None'."""
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "max_bot_token", "test-token")
    raw_user = '{"first_name":"NoId"}'
    response = client.get(
        "/api/auth/me", headers={"X-Init-Data": _make_init_data(raw_user)}
    )
    assert response.status_code == 401


@pytest.fixture
def substitution_data(db_session):
    manager = User(max_user_id="dev-user", full_name="Manager", role="manager")
    worker = User(max_user_id="f6-worker", full_name="Worker", role="responsible")
    obj = Object(code="obj-f6", name="Объект F6", execution_method="own")
    stage = Stage(code="st-f6", name="Этап F6")
    db_session.add_all([manager, worker, obj, stage])
    db_session.flush()
    db_session.add(ObjectStage(object_id=obj.id, stage_id=stage.id))
    db_session.add(
        ResponsibleObjectAssignment(
            user_id=worker.id,
            object_id=obj.id,
            active_from=date(2026, 1, 1),
            active_to=date(2026, 12, 31),
            schedule_type="daily",
        )
    )
    db_session.commit()
    return {"worker_id": worker.id, "obj_id": obj.id, "stage_id": stage.id}


def test_manager_can_submit_for_responsible(substitution_data):
    """F6.3: manager подаёт отчёт за ответственного."""
    payload = {
        "report_date": "2026-07-14",
        "object_id": substitution_data["obj_id"],
        "stage_id": substitution_data["stage_id"],
        "responsible_user_id": substitution_data["worker_id"],
        "staff": {"itr": 1, "internal": 0, "external": 0},
    }
    response = client.post(
        "/api/reports", json=payload, headers={"Idempotency-Key": "f6-subst-1"}
    )
    assert response.status_code == 201, response.text

    detail = client.get(f"/api/reports/{response.json()['id']}")
    assert detail.status_code == 200


def test_responsible_cannot_substitute(db_session):
    """F6.3: responsible не может подать отчёт за другого."""
    me = User(max_user_id="dev-user", full_name="Me", role="responsible")
    other = User(max_user_id="f6-other", full_name="Other", role="responsible")
    obj = Object(code="obj-f6b", name="Объект", execution_method="own")
    stage = Stage(code="st-f6b", name="Этап")
    db_session.add_all([me, other, obj, stage])
    db_session.flush()
    db_session.add(ObjectStage(object_id=obj.id, stage_id=stage.id))
    db_session.add(
        ResponsibleObjectAssignment(
            user_id=other.id,
            object_id=obj.id,
            active_from=date(2026, 1, 1),
            active_to=date(2026, 12, 31),
            schedule_type="daily",
        )
    )
    db_session.commit()

    payload = {
        "report_date": "2026-07-14",
        "object_id": obj.id,
        "stage_id": stage.id,
        "responsible_user_id": other.id,
        "staff": {"itr": 1, "internal": 0, "external": 0},
    }
    response = client.post(
        "/api/reports", json=payload, headers={"Idempotency-Key": "f6-subst-2"}
    )
    assert response.status_code == 422
    assert "руководителю" in response.text


def test_keyboard_attachment_contract():
    """F6.4: клавиатура сериализуется в документированный формат MAX."""
    from app.services.max_client import _keyboard_attachment

    attachment = _keyboard_attachment(
        [[{"text": "Кнопка", "callback_data": "do:1"}]]
    )
    assert attachment == {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [[{"type": "callback", "text": "Кнопка", "payload": "do:1"}]]
        },
    }
