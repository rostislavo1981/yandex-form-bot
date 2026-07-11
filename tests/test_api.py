"""Tests for backend.webapp_auth.verify_init_data and backend.api routes."""
from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Generator
from pathlib import Path
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.db import SubmissionDAO
from backend.webapp_auth import verify_init_data

# === verify_init_data =====================================================

BOT_TOKEN = "test-bot-token-12345"


def _make_init_data(
    user_id: int = 42, first_name: str = "Тест", auth_date: int | None = None
) -> str:
    """Build a properly-signed initData string for tests."""
    data: dict[str, str] = {
        "user": f'{{"id":{user_id},"first_name":"{first_name}"}}',
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "query_id": "abc123",
    }
    canonical = urlencode(sorted(data.items()))
    sig = hmac.new(
        hashlib.sha256(BOT_TOKEN.encode()).digest(),
        canonical.encode(),
        hashlib.sha256,
    ).hexdigest()
    data["hash"] = sig
    return urlencode(data)


def test_verify_init_data_valid() -> None:
    init = _make_init_data()
    result = verify_init_data(init, BOT_TOKEN)
    assert result["query_id"] == "abc123"
    assert "user" in result


def test_verify_init_data_bad_signature() -> None:
    init = _make_init_data() + "x"  # corrupt
    with pytest.raises(Exception):  # HTTPException
        verify_init_data(init, BOT_TOKEN)


def test_verify_init_data_missing_hash() -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        verify_init_data("user=test&auth_date=100", BOT_TOKEN)
    assert exc.value.status_code == 401


def test_verify_init_data_expired() -> None:
    init = _make_init_data(auth_date=int(time.time()) - 100_000)
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        verify_init_data(init, BOT_TOKEN)
    assert "expired" in str(exc.value.detail).lower() or exc.value.status_code == 401


def test_verify_init_data_empty() -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        verify_init_data("", BOT_TOKEN)
    assert exc.value.status_code == 401


# === API routes ===========================================================

@pytest.fixture
def _setup_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Generator[None, None, None]:
    """Set up: data dir, MAX_BOT_TOKEN, DB path."""
    monkeypatch.setenv("MAX_BOT_TOKEN", BOT_TOKEN)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from backend.config import reset_settings_cache

    reset_settings_cache()
    yield
    reset_settings_cache()


def test_healthz_no_auth(_setup_env: None) -> None:
    client = TestClient(create_app())
    r = client.get("/api/healthz")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_summary_requires_auth(_setup_env: None) -> None:
    client = TestClient(create_app())
    r = client.get("/api/summary")
    assert r.status_code == 401


def test_summary_with_valid_auth(_setup_env: None) -> None:
    # Insert 2 submissions
    from backend.schemas import Report

    s_dao = SubmissionDAO(_get_db_path())
    r1 = Report(date="2026-07-10", foreman="Степанов", object_name="РП-7",
                machines=[{"machine_type": "Экскаватор", "unit": "час", "quantity": 8}],
                personnel={"itr": 1, "opr_staff": 4, "opr_external": 0},
                waste_volume=15.0)
    r2 = Report(date="2026-07-10", foreman="Казнадеев", object_name="ТП-345",
                personnel={"itr": 1, "opr_staff": 2, "opr_external": 2},
                waste_volume=8.0)
    s_dao.insert(
        foreman=r1.foreman, date=r1.date.isoformat(), object_name=r1.object_name,
        report=r1.model_dump(mode="json"), screenshot_path="/tmp/x.png",
    )
    s_dao.insert(
        foreman=r2.foreman, date=r2.date.isoformat(), object_name=r2.object_name,
        report=r2.model_dump(mode="json"), screenshot_path="/tmp/y.png",
    )

    init = _make_init_data()
    client = TestClient(create_app())
    r = client.get(
        "/api/summary?date_from=2026-07-10&date_to=2026-07-10",
        headers={"X-Auth-InitData": init},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2
    assert body["submissions"][0]["foreman"] in ("Степанов", "Казнадеев")
    # personnel_total is computed
    assert body["submissions"][0]["personnel_total"] >= 3
    # screenshot_url built
    assert body["submissions"][0]["screenshot_url"] == "/api/screenshot/1"


def test_summary_filter_by_foreman(_setup_env: None) -> None:
    from backend.schemas import Report

    s_dao = SubmissionDAO(_get_db_path())
    r1 = Report(date="2026-07-10", foreman="Степанов", object_name="РП-7")
    r2 = Report(date="2026-07-10", foreman="Казнадеев", object_name="ТП-345")
    s_dao.insert(
        foreman=r1.foreman, date=r1.date.isoformat(), object_name=r1.object_name,
        report=r1.model_dump(mode="json"),
    )
    s_dao.insert(
        foreman=r2.foreman, date=r2.date.isoformat(), object_name=r2.object_name,
        report=r2.model_dump(mode="json"),
    )
    init = _make_init_data()
    client = TestClient(create_app())
    r = client.get(
        "/api/summary?date_from=2026-07-10&date_to=2026-07-10&foreman=Степанов",
        headers={"X-Auth-InitData": init},
    )
    assert r.status_code == 200
    assert r.json()["count"] == 1


def test_submission_404(_setup_env: None) -> None:
    init = _make_init_data()
    client = TestClient(create_app())
    r = client.get("/api/submissions/9999", headers={"X-Auth-InitData": init})
    assert r.status_code == 404


def test_screenshot_404_when_no_path(_setup_env: None) -> None:
    from backend.schemas import Report

    s_dao = SubmissionDAO(_get_db_path())
    r = Report(date="2026-07-10", foreman="X", object_name="Y")
    sid = s_dao.insert(
        foreman=r.foreman, date=r.date.isoformat(), object_name=r.object_name,
        report=r.model_dump(mode="json"),
    )
    init = _make_init_data()
    client = TestClient(create_app())
    r = client.get(f"/api/screenshot/{sid}", headers={"X-Auth-InitData": init})
    assert r.status_code == 404


def test_summary_xlsx(_setup_env: None) -> None:
    from backend.schemas import Report

    s_dao = SubmissionDAO(_get_db_path())
    r = Report(
        date="2026-07-10", foreman="Степанов", object_name="РП-7",
        personnel={"itr": 1, "opr_staff": 4, "opr_external": 0},
        waste_volume=15.0,
    )
    s_dao.insert(
        foreman=r.foreman, date=r.date.isoformat(), object_name=r.object_name,
        report=r.model_dump(mode="json"),
    )
    init = _make_init_data()
    client = TestClient(create_app())
    resp = client.get(
        "/api/summary.xlsx?date=2026-07-10",
        headers={"X-Auth-InitData": init},
    )
    assert resp.status_code == 200
    assert "spreadsheetml" in resp.headers.get("content-type", "")
    assert len(resp.content) > 1000


def test_summary_xlsx_no_data_404(_setup_env: None) -> None:
    init = _make_init_data()
    client = TestClient(create_app())
    resp = client.get(
        "/api/summary.xlsx?date=2020-01-01",
        headers={"X-Auth-InitData": init},
    )
    assert resp.status_code == 404


def test_root_returns_metadata(_setup_env: None) -> None:
    client = TestClient(create_app())
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "yandex-form-bot"
    assert "version" in body


# === helpers ===============================================================

def _get_db_path() -> Path:
    from backend.config import get_settings

    return get_settings().db_full_path
