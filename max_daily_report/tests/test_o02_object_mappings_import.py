from __future__ import annotations

from io import BytesIO

import pytest
from httpx import ASGITransport, AsyncClient
from openpyxl import Workbook
from sqlalchemy import select

from app.main import app
from app.models import Contract, ObjectContract
from app.services.excel_service import SHEET_COLUMNS, SHEET_ORDER

IMPORT_URL = "/api/catalogs/import"


@pytest.fixture(autouse=True)
def _admin_dev_user(db_session):
    """Import endpoints require manager/admin — pre-create dev-user as admin."""
    from app.models.users import User

    db_session.add(User(max_user_id="dev-user", full_name="Dev User", role="admin"))
    db_session.commit()


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def _build_workbook(rows_by_sheet: dict) -> bytes:
    wb = Workbook()
    wb.remove(wb.active)
    for sheet_name in SHEET_ORDER:
        ws = wb.create_sheet(title=sheet_name)
        ws.append(SHEET_COLUMNS[sheet_name])
        for row in rows_by_sheet.get(sheet_name, []):
            ws.append([row.get(col) for col in SHEET_COLUMNS[sheet_name]])
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _build_object_only(obj_code: str = "obj-1") -> dict:
    return {
        "Contractors": [
            {"code": "c1", "name": "Подрядчик 1", "active": 1, "sort_order": 1},
        ],
        "Objects": [
            {
                "code": obj_code,
                "name": "Объект 1",
                "execution_method": "own",
                "default_contractor_code": "c1",
                "active": 1,
                "sort_order": 1,
            },
        ],
    }


def _object_mapping_row(
    obj_code: str,
    short_name: str,
    contract_code: str,
    full_name: str,
    primary: int = 1,
    active: int = 1,
) -> dict:
    return {
        "object_code": obj_code,
        "short_name": short_name,
        "contract_code": contract_code,
        "full_name": full_name,
        "primary": primary,
        "active": active,
    }


async def test_import_object_mappings_happy_path(client, db_session):
    rows = _build_object_only()
    rows["ObjectMappings"] = [
        _object_mapping_row("obj-1", "Объект 1 (раб)", "ctr-1", "Договор 1", 1, 1),
    ]
    content = _build_workbook(rows)

    validate_resp = await client.post(
        f"{IMPORT_URL}/validate",
        files={"file": ("catalogs.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert validate_resp.status_code == 200
    body = validate_resp.json()
    assert body["valid"] is True

    apply_resp = await client.post(
        f"{IMPORT_URL}/apply",
        files={"file": ("catalogs.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert apply_resp.status_code == 200
    assert apply_resp.json()["status"] == "applied"

    contract = db_session.execute(
        select(Contract).where(Contract.code == "ctr-1")
    ).scalar_one()
    assert contract.full_name == "Договор 1"

    link = db_session.execute(
        select(ObjectContract).where(ObjectContract.contract_id == contract.id)
    ).scalar_one()
    assert link.is_primary is True
    assert link.active is True


async def test_import_object_mappings_skip_empty_contract(client, db_session):
    rows = _build_object_only()
    rows["ObjectMappings"] = [
        _object_mapping_row("obj-1", "Объект 1 (раб)", "??", "", 1, 1),
        _object_mapping_row("obj-1", "Объект 1 (раб)", "нет пока договора", "", 1, 1),
    ]
    content = _build_workbook(rows)

    apply_resp = await client.post(
        f"{IMPORT_URL}/apply",
        files={"file": ("catalogs.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert apply_resp.status_code == 200

    assert db_session.execute(select(Contract)).scalar_one_or_none() is None
    assert db_session.execute(select(ObjectContract)).scalar_one_or_none() is None


async def test_import_object_mappings_idempotent(client, db_session):
    rows = _build_object_only()
    rows["ObjectMappings"] = [
        _object_mapping_row("obj-1", "Объект 1 (раб)", "ctr-1", "Договор 1", 1, 1),
        _object_mapping_row("obj-1", "Объект 1 (раб)", "ctr-2", "Договор 2", 0, 1),
    ]
    content = _build_workbook(rows)

    for _ in range(2):
        apply_resp = await client.post(
            f"{IMPORT_URL}/apply",
            files={"file": ("catalogs.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert apply_resp.status_code == 200

    assert len(db_session.execute(select(Contract)).scalars().all()) == 2
    assert len(db_session.execute(select(ObjectContract)).scalars().all()) == 2


async def test_import_object_mappings_rollback_on_error(client, db_session):
    rows = _build_object_only()
    rows["ObjectMappings"] = [
        _object_mapping_row("obj-1", "Объект 1 (раб)", "ctr-1", "Договор 1", 1, 1),
        _object_mapping_row("obj-missing", "Нет объекта", "ctr-2", "Договор 2", 1, 1),
    ]
    content = _build_workbook(rows)

    apply_resp = await client.post(
        f"{IMPORT_URL}/apply",
        files={"file": ("catalogs.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert apply_resp.status_code == 422

    assert db_session.execute(select(Contract).where(Contract.code == "ctr-1")).scalar_one_or_none() is None
    assert db_session.execute(select(ObjectContract)).scalar_one_or_none() is None


async def test_import_object_mappings_duplicate_pair_rejected(client, db_session):
    rows = _build_object_only()
    rows["ObjectMappings"] = [
        _object_mapping_row("obj-1", "Объект 1 (раб)", "ctr-1", "Договор 1", 1, 1),
        _object_mapping_row("obj-1", "Объект 1 (раб)", "ctr-1", "Договор 1 дубль", 1, 1),
    ]
    content = _build_workbook(rows)

    validate_resp = await client.post(
        f"{IMPORT_URL}/validate",
        files={"file": ("catalogs.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert validate_resp.status_code == 200
    body = validate_resp.json()
    assert body["valid"] is False
    assert any(
        "Дублирующаяся пара (object_code, contract_code)" in err["message"]
        for err in body["errors"]
    )

    apply_resp = await client.post(
        f"{IMPORT_URL}/apply",
        files={"file": ("catalogs.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert apply_resp.status_code == 422
