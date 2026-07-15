from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import AsyncSessionLocal
from app.main import app

ADMIN_BASE = "/api/admin/catalogs"


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def admin_session():
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
def bypass_auth(monkeypatch):
    monkeypatch.setattr("app.api.admin_catalogs._require_manager", lambda user: None)


@pytest.fixture
async def sample_data(admin_session):
    from app.models.catalogs import Contractor, Object, Stage, Unit
    from app.models.users import User

    contractor = Contractor(code="cntr-1", name="Подрядчик 1")
    unit = Unit(code="m3", name="куб", symbol="м³")
    stage = Stage(code="stg-1", name="Этап 1")
    obj = Object(code="obj-1", name="Объект 1", execution_method="own")
    user = User(max_user_id="max-user-1", full_name="User 1", role="responsible")

    admin_session.add_all([contractor, unit, stage, obj, user])
    await admin_session.commit()
    for item in (contractor, unit, stage, obj, user):
        await admin_session.refresh(item)

    return {
        "contractor": contractor,
        "unit": unit,
        "stage": stage,
        "object": obj,
        "user": user,
    }


@pytest.mark.asyncio
async def test_admin_objects_crud_and_soft_delete(client, bypass_auth, admin_session):
    create_resp = await client.post(
        f"{ADMIN_BASE}/objects",
        json={
            "code": "obj-test",
            "name": "Тестовый объект",
            "active": True,
            "sort_order": 1,
            "execution_method": "own",
            "default_contractor_id": None,
        },
        headers={"X-Init-Data": "dev"},
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["code"] == "obj-test"
    obj_id = created["id"]

    list_resp = await client.get(f"{ADMIN_BASE}/objects", headers={"X-Init-Data": "dev"})
    assert list_resp.status_code == 200
    assert any(item["id"] == obj_id for item in list_resp.json())

    update_resp = await client.put(
        f"{ADMIN_BASE}/objects/{obj_id}",
        json={
            "code": "obj-test-upd",
            "name": "Обновлённый",
            "active": True,
            "sort_order": 2,
            "execution_method": "contractor",
            "default_contractor_id": None,
        },
        headers={"X-Init-Data": "dev"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["code"] == "obj-test-upd"

    dup_resp = await client.post(
        f"{ADMIN_BASE}/objects",
        json={
            "code": "obj-test-upd",
            "name": "Дубль",
            "active": True,
            "execution_method": "own",
        },
        headers={"X-Init-Data": "dev"},
    )
    assert dup_resp.status_code == 409

    del_resp = await client.delete(f"{ADMIN_BASE}/objects/{obj_id}", headers={"X-Init-Data": "dev"})
    assert del_resp.status_code == 204

    from app.models.catalogs import Object

    obj = await admin_session.get(Object, obj_id)
    assert obj is not None
    assert obj.active is False


@pytest.mark.asyncio
async def test_admin_stages_crud(client, bypass_auth):
    resp = await client.post(
        f"{ADMIN_BASE}/stages",
        json={"code": "stg-test", "name": "Этап тест", "active": True, "sort_order": 5},
        headers={"X-Init-Data": "dev"},
    )
    assert resp.status_code == 201
    stage_id = resp.json()["id"]

    resp = await client.put(
        f"{ADMIN_BASE}/stages/{stage_id}",
        json={"code": "stg-test", "name": "Этап обновлён", "active": False, "sort_order": 6},
        headers={"X-Init-Data": "dev"},
    )
    assert resp.status_code == 200
    assert resp.json()["active"] is False


@pytest.mark.asyncio
async def test_admin_units_crud(client, bypass_auth):
    resp = await client.post(
        f"{ADMIN_BASE}/units",
        json={"code": "t", "name": "тонна", "symbol": "т", "active": True},
        headers={"X-Init-Data": "dev"},
    )
    assert resp.status_code == 201
    unit_id = resp.json()["id"]

    resp = await client.put(
        f"{ADMIN_BASE}/units/{unit_id}",
        json={"code": "t", "name": "тонна", "symbol": "т", "active": True, "sort_order": 3},
        headers={"X-Init-Data": "dev"},
    )
    assert resp.status_code == 200
    assert resp.json()["sort_order"] == 3


@pytest.mark.asyncio
async def test_admin_contractors_crud(client, bypass_auth):
    resp = await client.post(
        f"{ADMIN_BASE}/contractors",
        json={"code": "ctr-test", "name": "ООО Тест", "active": True},
        headers={"X-Init-Data": "dev"},
    )
    assert resp.status_code == 201
    contractor_id = resp.json()["id"]

    resp = await client.delete(
        f"{ADMIN_BASE}/contractors/{contractor_id}", headers={"X-Init-Data": "dev"}
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_admin_equipment_and_work_types_crud(client, bypass_auth, admin_session):
    from app.models.catalogs import Unit

    unit = Unit(code="hm", name="час-машина", symbol="ч/м")
    admin_session.add(unit)
    await admin_session.commit()
    await admin_session.refresh(unit)

    resp = await client.post(
        f"{ADMIN_BASE}/equipment",
        json={"code": "exc", "name": "Экскаватор", "active": True, "default_unit_id": unit.id},
        headers={"X-Init-Data": "dev"},
    )
    assert resp.status_code == 201
    eq_id = resp.json()["id"]

    resp = await client.put(
        f"{ADMIN_BASE}/equipment/{eq_id}",
        json={"code": "exc", "name": "Экскаватор JCB", "active": True, "default_unit_id": unit.id},
        headers={"X-Init-Data": "dev"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Экскаватор JCB"

    resp = await client.post(
        f"{ADMIN_BASE}/work-types",
        json={"code": "zem", "name": "Земляные", "active": True, "default_unit_id": unit.id},
        headers={"X-Init-Data": "dev"},
    )
    assert resp.status_code == 201
    wt_id = resp.json()["id"]

    resp = await client.get(f"{ADMIN_BASE}/work-types", headers={"X-Init-Data": "dev"})
    assert resp.status_code == 200
    assert any(item["id"] == wt_id for item in resp.json())


@pytest.mark.asyncio
async def test_admin_work_methods_crud(client, bypass_auth):
    resp = await client.post(
        f"{ADMIN_BASE}/work-methods",
        json={"code": "m-manual", "name": "Ручной", "active": True},
        headers={"X-Init-Data": "dev"},
    )
    assert resp.status_code == 201
    method_id = resp.json()["id"]

    resp = await client.delete(
        f"{ADMIN_BASE}/work-methods/{method_id}", headers={"X-Init-Data": "dev"}
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_admin_object_stages_link_crud(client, bypass_auth, sample_data):
    resp = await client.post(
        f"{ADMIN_BASE}/object-stages",
        json={"object_id": sample_data["object"].id, "stage_id": sample_data["stage"].id, "active": True},
        headers={"X-Init-Data": "dev"},
    )
    assert resp.status_code == 201
    link_id = resp.json()["id"]

    resp = await client.get(f"{ADMIN_BASE}/object-stages", headers={"X-Init-Data": "dev"})
    assert resp.status_code == 200
    assert any(item["id"] == link_id for item in resp.json())

    resp = await client.delete(
        f"{ADMIN_BASE}/object-stages/{link_id}", headers={"X-Init-Data": "dev"}
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_admin_work_type_methods_link_crud(client, bypass_auth, admin_session):
    from app.models.catalogs import WorkMethod, WorkType

    wt = WorkType(code="wt-1", name="Вид 1")
    wm = WorkMethod(code="wm-1", name="Способ 1")
    admin_session.add_all([wt, wm])
    await admin_session.commit()
    await admin_session.refresh(wt)
    await admin_session.refresh(wm)

    resp = await client.post(
        f"{ADMIN_BASE}/work-type-methods",
        json={"work_type_id": wt.id, "work_method_id": wm.id, "active": True},
        headers={"X-Init-Data": "dev"},
    )
    assert resp.status_code == 201
    link_id = resp.json()["id"]

    resp = await client.delete(
        f"{ADMIN_BASE}/work-type-methods/{link_id}", headers={"X-Init-Data": "dev"}
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_admin_assignments_and_users_crud(client, bypass_auth, sample_data):
    resp = await client.post(
        f"{ADMIN_BASE}/assignments",
        json={
            "user_id": sample_data["user"].id,
            "object_id": sample_data["object"].id,
            "active_from": "2026-01-01",
            "active_to": "2026-12-31",
            "schedule_type": "daily",
            "active": True,
        },
        headers={"X-Init-Data": "dev"},
    )
    assert resp.status_code == 201
    assignment_id = resp.json()["id"]

    resp = await client.get(f"{ADMIN_BASE}/assignments", headers={"X-Init-Data": "dev"})
    assert resp.status_code == 200
    assert any(item["id"] == assignment_id for item in resp.json())

    resp = await client.delete(
        f"{ADMIN_BASE}/assignments/{assignment_id}", headers={"X-Init-Data": "dev"}
    )
    assert resp.status_code == 204

    resp = await client.post(
        f"{ADMIN_BASE}/users",
        json={"max_user_id": "max-admin-1", "full_name": "Admin One", "role": "admin", "active": True},
        headers={"X-Init-Data": "dev"},
    )
    assert resp.status_code == 201
    user_id = resp.json()["id"]

    resp = await client.put(
        f"{ADMIN_BASE}/users/{user_id}",
        json={"max_user_id": "max-admin-1", "full_name": "Admin One Updated", "role": "manager", "active": True},
        headers={"X-Init-Data": "dev"},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "manager"
    assert resp.json()["full_name"] == "Admin One Updated"


@pytest.mark.asyncio
async def test_admin_endpoints_reject_responsible_role(client, monkeypatch):
    from app.models.users import User

    async with AsyncSessionLocal() as session:
        user = User(max_user_id="resp-only", full_name="Resp", role="responsible")
        session.add(user)
        await session.commit()
        await session.refresh(user)

    monkeypatch.setattr("app.api.admin_catalogs._extract_user", lambda request: user)

    resp = await client.get(f"{ADMIN_BASE}/objects", headers={"X-Init-Data": "dev"})
    assert resp.status_code == 403
