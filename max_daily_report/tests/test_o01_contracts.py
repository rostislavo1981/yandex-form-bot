from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Contract, Object, ObjectContract


def test_one_object_one_contract(db_session) -> None:
    suffix = uuid.uuid4().hex[:8]
    obj = Object(code=f"obj-{suffix}", name="Объект 1")
    contract = Contract(code=f"ctr-{suffix}", full_name="Договор 1")
    db_session.add_all([obj, contract])
    db_session.flush()

    link = ObjectContract(object_id=obj.id, contract_id=contract.id)
    db_session.add(link)
    db_session.commit()

    result = db_session.execute(
        select(ObjectContract).where(
            ObjectContract.object_id == obj.id,
            ObjectContract.contract_id == contract.id,
        )
    )
    found = result.scalar_one()
    assert found is not None
    assert found.object_id == obj.id
    assert found.contract_id == contract.id


def test_one_object_two_contracts(db_session) -> None:
    suffix = uuid.uuid4().hex[:8]
    obj = Object(code=f"obj-{suffix}", name="Объект 1")
    contract1 = Contract(code=f"ctr1-{suffix}", full_name="Договор 1")
    contract2 = Contract(code=f"ctr2-{suffix}", full_name="Договор 2")
    db_session.add_all([obj, contract1, contract2])
    db_session.flush()

    link1 = ObjectContract(object_id=obj.id, contract_id=contract1.id)
    link2 = ObjectContract(object_id=obj.id, contract_id=contract2.id)
    db_session.add_all([link1, link2])
    db_session.commit()

    result = db_session.execute(
        select(ObjectContract).where(ObjectContract.object_id == obj.id)
    )
    links = result.scalars().all()
    assert len(links) == 2


def test_one_contract_two_objects(db_session) -> None:
    suffix = uuid.uuid4().hex[:8]
    obj1 = Object(code=f"obj1-{suffix}", name="Объект 1")
    obj2 = Object(code=f"obj2-{suffix}", name="Объект 2")
    contract = Contract(code=f"ctr-{suffix}", full_name="Договор 1")
    db_session.add_all([obj1, obj2, contract])
    db_session.flush()

    link1 = ObjectContract(object_id=obj1.id, contract_id=contract.id)
    link2 = ObjectContract(object_id=obj2.id, contract_id=contract.id)
    db_session.add_all([link1, link2])
    db_session.commit()

    result = db_session.execute(
        select(ObjectContract).where(ObjectContract.contract_id == contract.id)
    )
    links = result.scalars().all()
    assert len(links) == 2


def test_duplicate_link_rejected(db_session) -> None:
    suffix = uuid.uuid4().hex[:8]
    obj = Object(code=f"obj-{suffix}", name="Объект 1")
    contract = Contract(code=f"ctr-{suffix}", full_name="Договор 1")
    db_session.add_all([obj, contract])
    db_session.flush()

    link1 = ObjectContract(object_id=obj.id, contract_id=contract.id)
    db_session.add(link1)
    db_session.commit()

    link2 = ObjectContract(object_id=obj.id, contract_id=contract.id)
    db_session.add(link2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_daily_report_nullable_contract_id(db_session) -> None:
    suffix = uuid.uuid4().hex[:8]
    from app.models import DailyReport, Stage, User

    user = User(max_user_id=f"user-{suffix}", full_name="User", role="responsible")
    obj = Object(code=f"obj-{suffix}", name="Объект 1")
    stage = Stage(code=f"stg-{suffix}", name="Этап 1")
    db_session.add_all([user, obj, stage])
    db_session.flush()

    report = DailyReport(
        report_date="2026-07-15",
        responsible_user_id=user.id,
        object_id=obj.id,
        stage_id=stage.id,
        object_name_snapshot="Объект 1",
        idempotency_key=f"key-{suffix}",
        contract_id=None,
    )
    db_session.add(report)
    db_session.commit()

    found = db_session.get(DailyReport, report.id)
    assert found is not None
    assert found.contract_id is None
