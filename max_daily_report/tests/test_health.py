from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def test_health_endpoint_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app_name"] == settings.app_name
    assert body["version"] == settings.version


def test_readiness_endpoint_checks_database() -> None:
    client = TestClient(app)
    response = client.get("/api/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
