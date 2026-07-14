"""F1 regression tests: production auth, role checks, internal endpoints."""
from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.models.catalogs import Object, ObjectStage, Stage, Unit
from app.models.reports import ResponsibleObjectAssignment
from app.models.users import User

client = TestClient(app)


@pytest.fixture
def prod_env(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "max_bot_token", "test-token")


# --- F1.1: production requires initData on every protected endpoint ---


def test_reports_list_requires_init_data_in_prod(prod_env):
    response = client.get("/api/reports")
    assert response.status_code == 401


def test_catalogs_search_requires_init_data_in_prod(prod_env):
    response = client.get("/api/catalogs/objects")
    assert response.status_code == 401


def test_timesheet_requires_init_data_in_prod(prod_env):
    response = client.get(
        "/api/timesheet/1", params={"date_from": "2026-07-01", "date_to": "2026-07-02"}
    )
    assert response.status_code == 401


def test_admin_catalogs_requires_init_data_in_prod(prod_env):
    response = client.get("/api/admin/catalogs/objects")
    assert response.status_code == 401


def test_dev_header_rejected_in_prod(prod_env):
    response = client.get("/api/reports", headers={"X-Init-Data": "dev"})
    assert response.status_code == 401


# --- F1.2: import/export requires manager/admin ---


def test_catalog_export_forbidden_for_responsible(db_session):
    db_session.add(User(max_user_id="dev-user", full_name="Dev", role="responsible"))
    db_session.commit()
    response = client.get("/api/catalogs/export.xlsx")
    assert response.status_code == 403


def test_catalog_export_allowed_for_admin(db_session):
    db_session.add(User(max_user_id="dev-user", full_name="Dev", role="admin"))
    db_session.commit()
    response = client.get("/api/catalogs/export.xlsx")
    assert response.status_code == 200


# --- F1.2: internal endpoints require token when configured ---


def test_scheduler_rejected_without_token(monkeypatch):
    monkeypatch.setattr(settings, "internal_token", "sekret")
    response = client.post("/api/scheduler/morning")
    assert response.status_code == 401


def test_scheduler_rejected_with_wrong_token(monkeypatch):
    monkeypatch.setattr(settings, "internal_token", "sekret")
    response = client.post(
        "/api/scheduler/morning", headers={"X-Internal-Token": "wrong"}
    )
    assert response.status_code == 401


def test_scheduler_accepts_valid_token(monkeypatch):
    monkeypatch.setattr(settings, "internal_token", "sekret")
    response = client.post(
        "/api/scheduler/morning", headers={"X-Internal-Token": "sekret"}
    )
    assert response.status_code == 200


def test_worker_rejected_in_prod_without_token(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "internal_token", "")
    response = client.post("/api/worker/process-outbox")
    assert response.status_code == 401


# --- F1.3: report detail ownership ---


@pytest.mark.asyncio
async def test_report_detail_forbidden_for_foreign_responsible(db_session):
    from app.database import AsyncSessionLocal
    from app.schemas.reports import ReportCreateRequest
    from app.services.report_service import ReportService

    dev_user = User(max_user_id="dev-user", full_name="Dev", role="responsible")
    other = User(max_user_id="other-1", full_name="Other", role="responsible")
    unit = Unit(code="h", name="час", symbol="ч")
    obj = Object(code="obj-own-1", name="Объект", execution_method="own")
    stage = Stage(code="st-1", name="Этап")
    db_session.add_all([dev_user, other, unit, obj, stage])
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
    other_id = other.id
    obj_id = obj.id
    stage_id = stage.id

    async with AsyncSessionLocal() as session:
        other_user = await session.get(User, other_id)
        service = ReportService(session)
        report = await service.create(
            other_user,
            ReportCreateRequest(
                report_date=date(2026, 7, 14),
                object_id=obj_id,
                stage_id=stage_id,
                staff={"itr": 1, "internal": 0, "external": 0},
            ),
            "key-access-1",
        )
        report_id = report.id

    response = client.get(f"/api/reports/{report_id}")
    assert response.status_code == 403


# --- F1.4: objects restricted by assignment for responsible ---


def test_objects_search_restricted_for_responsible(db_session):
    dev_user = User(max_user_id="dev-user", full_name="Dev", role="responsible")
    obj_mine = Object(code="obj-mine", name="Мой объект", execution_method="own")
    obj_other = Object(code="obj-other", name="Чужой объект", execution_method="own")
    db_session.add_all([dev_user, obj_mine, obj_other])
    db_session.flush()
    db_session.add(
        ResponsibleObjectAssignment(
            user_id=dev_user.id,
            object_id=obj_mine.id,
            active_from=date(2026, 1, 1),
            active_to=date(2026, 12, 31),
            schedule_type="daily",
        )
    )
    db_session.commit()

    response = client.get("/api/catalogs/objects")
    assert response.status_code == 200
    body = response.json()
    codes = [item["code"] for item in body["items"]]
    assert codes == ["obj-mine"]
    assert body["total"] == 1


def test_objects_search_unrestricted_for_manager(db_session):
    dev_user = User(max_user_id="dev-user", full_name="Dev", role="manager")
    obj_a = Object(code="obj-a", name="Объект А", execution_method="own")
    obj_b = Object(code="obj-b", name="Объект Б", execution_method="own")
    db_session.add_all([dev_user, obj_a, obj_b])
    db_session.commit()

    response = client.get("/api/catalogs/objects")
    assert response.status_code == 200
    assert response.json()["total"] == 2
