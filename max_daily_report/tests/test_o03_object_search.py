from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import app

from app.models.catalogs import Object
from app.models.contracts import Contract, ObjectContract
from app.models.reports import ResponsibleObjectAssignment
from app.models.users import User

client = TestClient(app)


@pytest.fixture(autouse=True)
def _manager_dev_user(db_session):
    db_session.add(User(max_user_id="dev-user", full_name="Dev User", role="manager"))
    db_session.commit()


def test_search_by_short_name(db_session):
    obj = Object(code="OBJ-001", name="Пискаревский", execution_method="own")
    db_session.add(obj)
    db_session.commit()

    response = client.get("/api/catalogs/objects?q=Пискар")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == obj.id


def test_search_by_contract_code(db_session):
    obj = Object(code="OBJ-002", name="Объект 2", execution_method="own")
    contract = Contract(code="RT-26-1-05", full_name="РТ_26-1-05СМР договор")
    db_session.add_all([obj, contract])
    db_session.flush()
    db_session.add(ObjectContract(object_id=obj.id, contract_id=contract.id))
    db_session.commit()

    response = client.get("/api/catalogs/objects?q=RT-26-1-05")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == obj.id


def test_search_by_full_name(db_session):
    obj = Object(code="OBJ-003", name="Объект 3", execution_method="own")
    contract = Contract(code="CTR-003", full_name="Очень длинное название договора на строительство")
    db_session.add_all([obj, contract])
    db_session.flush()
    db_session.add(ObjectContract(object_id=obj.id, contract_id=contract.id))
    db_session.commit()

    response = client.get("/api/catalogs/objects?q=длинное название")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == obj.id


def test_responsible_sees_only_assigned(db_session):
    dev_user = db_session.query(User).filter(User.max_user_id == "dev-user").first()
    assert dev_user is not None
    dev_user.role = "responsible"
    dev_user.full_name = "Dev"
    db_session.commit()

    obj_mine = Object(code="obj-mine", name="Мой объект", execution_method="own")
    obj_other = Object(code="obj-other", name="Чужой объект", execution_method="own")
    db_session.add_all([obj_mine, obj_other])
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


def test_inactive_hidden(db_session):
    active_obj = Object(code="obj-active", name="Активный объект", execution_method="own")
    inactive_obj = Object(
        code="obj-inactive", name="Неактивный объект", execution_method="own", active=False
    )
    db_session.add_all([active_obj, inactive_obj])
    db_session.commit()

    response = client.get("/api/catalogs/objects?q=объект")
    assert response.status_code == 200
    body = response.json()
    ids = [item["id"] for item in body["items"]]
    assert active_obj.id in ids
    assert inactive_obj.id not in ids


def test_api_returns_contracts(db_session):
    obj = Object(code="OBJ-004", name="Объект 4", execution_method="own")
    contract1 = Contract(code="CTR-A", full_name="Договор А")
    contract2 = Contract(code="CTR-B", full_name="Договор Б")
    db_session.add_all([obj, contract1, contract2])
    db_session.flush()
    db_session.add_all([
        ObjectContract(object_id=obj.id, contract_id=contract1.id, is_primary=True),
        ObjectContract(object_id=obj.id, contract_id=contract2.id, is_primary=False),
    ])
    db_session.commit()

    response = client.get("/api/catalogs/objects?q=Объект 4")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["id"] == obj.id
    assert len(item["contracts"]) == 2
    contract_codes = {c["code"] for c in item["contracts"]}
    assert contract_codes == {"CTR-A", "CTR-B"}
    for c in item["contracts"]:
        assert "id" in c
        assert "full_name" in c
        assert "primary" in c
        if c["code"] == "CTR-A":
            assert c["primary"] is True
        if c["code"] == "CTR-B":
            assert c["primary"] is False
