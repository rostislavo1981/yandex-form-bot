from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_search_contractors(client, db_session):
    from app.models.catalogs import Contractor

    c1 = Contractor(code="CONTR-1", name="Подрядчик 1", active=True)
    c2 = Contractor(code="CONTR-2", name="Подрядчик 2", active=True)
    c3 = Contractor(code="OLD-1", name="Старый подрядчик", active=False)
    db_session.add_all([c1, c2, c3])
    db_session.commit()

    response = client.get(
        "/api/catalogs/contractors",
        headers={"x-init-data": "dev"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    codes = [item["code"] for item in data["items"]]
    assert "CONTR-1" in codes
    assert "CONTR-2" in codes
    assert "OLD-1" not in codes


def test_search_contractors_by_name(client, db_session):
    from app.models.catalogs import Contractor

    c1 = Contractor(code="ABC", name="Альфа Строй", active=True)
    c2 = Contractor(code="XYZ", name="Бета Девелопмент", active=True)
    db_session.add_all([c1, c2])
    db_session.commit()

    response = client.get(
        "/api/catalogs/contractors",
        params={"q": "альфа"},
        headers={"x-init-data": "dev"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["code"] == "ABC"
