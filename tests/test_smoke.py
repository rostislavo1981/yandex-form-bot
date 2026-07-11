"""Smoke tests: package imports + healthz route."""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend import __version__
from backend.app import create_app


def test_healthz_returns_ok() -> None:
    client = TestClient(create_app())
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body == {"ok": True, "version": __version__}


def test_create_app_is_idempotent() -> None:
    """create_app() must produce a fresh app each call (no shared state)."""
    app1 = create_app()
    app2 = create_app()
    assert app1 is not app2
    assert app1.title == app2.title
