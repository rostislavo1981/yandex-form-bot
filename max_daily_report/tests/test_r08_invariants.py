from __future__ import annotations

from datetime import date

import pytest

from app.models.catalogs import Object, ObjectStage, Stage
from app.models.reports import ResponsibleObjectAssignment
from app.models.users import User
from app.schemas.reports import ReportCreateRequest, StaffInput
from app.services.report_service import ReportDuplicateError, ReportService


async def _seed(session):
    user = User(max_user_id="max-race", full_name="Race User", role="responsible")
    obj = Object(code="OBJ-RACE", name="Race Obj", active=True)
    stage = Stage(code="STG-RACE", name="Race Stage", active=True)
    session.add_all([user, obj, stage])
    await session.flush()
    session.add(ObjectStage(object_id=obj.id, stage_id=stage.id))
    session.add(ResponsibleObjectAssignment(
        user_id=user.id, object_id=obj.id,
        active_from=date(2026, 1, 1), active_to=date(2026, 12, 31),
        schedule_type="daily",
    ))
    await session.commit()
    return user, obj, stage


@pytest.mark.asyncio
async def test_duplicate_report_returns_409(async_session):
    user, obj, stage = await _seed(async_session)

    data = ReportCreateRequest(
        report_date=date(2026, 7, 15),
        object_id=obj.id,
        stage_id=stage.id,
        staff=StaffInput(itr=1),
    )
    service = ReportService(async_session)
    report1 = await service.create(user, data, "idem-race-1")
    assert report1.id is not None

    with pytest.raises(ReportDuplicateError):
        await service.create(user, data, "idem-race-2")


@pytest.mark.asyncio
async def test_idempotency_key_returns_same_report(async_session):
    user, obj, stage = await _seed(async_session)

    data = ReportCreateRequest(
        report_date=date(2026, 7, 15),
        object_id=obj.id,
        stage_id=stage.id,
        staff=StaffInput(itr=1),
    )
    service = ReportService(async_session)
    report1 = await service.create(user, data, "idem-same")
    report2 = await service.create(user, data, "idem-same")
    assert report1.id == report2.id


@pytest.mark.asyncio
async def test_different_keys_same_day_rejected(async_session):
    user, obj, stage = await _seed(async_session)

    data = ReportCreateRequest(
        report_date=date(2026, 7, 15),
        object_id=obj.id,
        stage_id=stage.id,
        staff=StaffInput(itr=1),
    )
    service = ReportService(async_session)
    await service.create(user, data, "key-1")

    with pytest.raises(ReportDuplicateError):
        await service.create(user, data, "key-2")


@pytest.mark.asyncio
async def test_same_report_different_dates_allowed(async_session):
    user, obj, stage = await _seed(async_session)

    data1 = ReportCreateRequest(
        report_date=date(2026, 7, 14),
        object_id=obj.id,
        stage_id=stage.id,
        staff=StaffInput(itr=1),
    )
    data2 = ReportCreateRequest(
        report_date=date(2026, 7, 15),
        object_id=obj.id,
        stage_id=stage.id,
        staff=StaffInput(itr=2),
    )
    service = ReportService(async_session)
    report1 = await service.create(user, data1, "key-jul14")
    report2 = await service.create(user, data2, "key-jul15")
    assert report1.id != report2.id
