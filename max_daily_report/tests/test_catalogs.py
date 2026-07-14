from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.catalogs import (
    EquipmentType,
    Object,
    ObjectStage,
    Stage,
    Unit,
    WorkMethod,
    WorkType,
    WorkTypeMethod,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def _manager_dev_user(db_session):
    """Search semantics are tested under manager (sees all objects).

    Responsible-role restriction is covered in test_access_control.py.
    """
    from app.models.users import User

    db_session.add(User(max_user_id="dev-user", full_name="Dev User", role="manager"))
    db_session.commit()


def _suffix():
    return uuid.uuid4().hex[:8]


def _seed_catalogs(db_session: Session):
    s = _suffix()
    unit = Unit(code=f"m3-{s}", name="кубометр", symbol="м³")
    db_session.add(unit)
    db_session.flush()

    obj = Object(code=f"obj-{s}", name=f"Объект {s}", execution_method="own")
    other_obj = Object(
        code=f"other-{s}", name="Другой объект", execution_method="own"
    )
    stage_a = Stage(code=f"st-a-{s}", name="Подготовка")
    stage_b = Stage(code=f"st-b-{s}", name="Нулевой цикл")
    other_stage = Stage(code=f"st-other-{s}", name="Чужой этап")
    db_session.add_all([obj, other_obj, stage_a, stage_b, other_stage])
    db_session.flush()

    db_session.add_all(
        [
            ObjectStage(object_id=obj.id, stage_id=stage_a.id),
            ObjectStage(object_id=obj.id, stage_id=stage_b.id),
            ObjectStage(object_id=other_obj.id, stage_id=other_stage.id),
        ]
    )

    equipment = EquipmentType(
        code=f"exc-{s}", name="Экскаватор 200", default_unit_id=unit.id
    )
    db_session.add(equipment)

    work_type = WorkType(
        code=f"dig-{s}", name="Земляные работы", default_unit_id=unit.id
    )
    method = WorkMethod(code=f"manual-{s}", name="Вручную")
    db_session.add_all([work_type, method])
    db_session.flush()
    db_session.add(WorkTypeMethod(work_type_id=work_type.id, work_method_id=method.id))

    db_session.commit()
    return {
        "object_id": obj.id,
        "other_object_id": other_obj.id,
        "stage_a_id": stage_a.id,
        "stage_b_id": stage_b.id,
        "other_stage_id": other_stage.id,
        "equipment_id": equipment.id,
        "work_type_id": work_type.id,
        "method_id": method.id,
        "suffix": s,
    }


def test_search_objects_by_partial_russian_name(db_session: Session) -> None:
    data = _seed_catalogs(db_session)
    response = client.get("/api/catalogs/objects?q=объект")
    assert response.status_code == 200
    body = response.json()
    ids = {item["id"] for item in body["items"]}
    assert data["object_id"] in ids
    assert body["total"] >= 1


def test_search_objects_by_code(db_session: Session) -> None:
    data = _seed_catalogs(db_session)
    response = client.get(f"/api/catalogs/objects?q=obj-{data['suffix']}")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == data["object_id"]


def test_search_objects_excludes_inactive(db_session: Session) -> None:
    data = _seed_catalogs(db_session)
    inactive = Object(
        code=f"obj-inactive-{data['suffix']}",
        name="Неактивный объект",
        execution_method="own",
        active=False,
    )
    db_session.add(inactive)
    db_session.commit()

    response = client.get("/api/catalogs/objects?q=неактивный")
    assert response.status_code == 200
    body = response.json()
    assert not any(item["id"] == inactive.id for item in body["items"])


def test_search_stages_for_object(db_session: Session) -> None:
    data = _seed_catalogs(db_session)
    response = client.get(f"/api/catalogs/objects/{data['object_id']}/stages")
    assert response.status_code == 200
    body = response.json()
    ids = {item["id"] for item in body["items"]}
    assert data["stage_a_id"] in ids
    assert data["stage_b_id"] in ids
    assert data["other_stage_id"] not in ids


def test_search_stages_filters_by_query(db_session: Session) -> None:
    data = _seed_catalogs(db_session)
    response = client.get(
        f"/api/catalogs/objects/{data['object_id']}/stages?q=подготов"
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == data["stage_a_id"]


def test_search_equipment(db_session: Session) -> None:
    data = _seed_catalogs(db_session)
    response = client.get("/api/catalogs/equipment?q=экскав")
    assert response.status_code == 200
    body = response.json()
    assert any(item["id"] == data["equipment_id"] for item in body["items"])


def test_search_work_types(db_session: Session) -> None:
    data = _seed_catalogs(db_session)
    response = client.get("/api/catalogs/work-types?q=землян")
    assert response.status_code == 200
    body = response.json()
    assert any(item["id"] == data["work_type_id"] for item in body["items"])


def test_search_methods_for_work_type(db_session: Session) -> None:
    data = _seed_catalogs(db_session)
    response = client.get(f"/api/catalogs/work-types/{data['work_type_id']}/methods")
    assert response.status_code == 200
    body = response.json()
    assert any(item["id"] == data["method_id"] for item in body["items"])


def test_list_units(db_session: Session) -> None:
    _seed_catalogs(db_session)
    response = client.get("/api/catalogs/units")
    assert response.status_code == 200
    body = response.json()
    assert any(item["symbol"] == "м³" for item in body["items"])


def test_pagination_limit(db_session: Session) -> None:
    s = _suffix()
    for i in range(5):
        db_session.add(Object(code=f"obj-pag-{s}-{i}", name=f"Объект паг {i}"))
    db_session.commit()

    response = client.get("/api/catalogs/objects?q=объект паг&limit=2&offset=0")
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    assert body["total"] >= 5
