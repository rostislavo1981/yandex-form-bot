from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select

from app.models.catalogs import EquipmentType, Object, ObjectStage, Stage, Unit, WorkType
from app.models.reports import ResponsibleObjectAssignment
from app.models.users import User
from app.schemas.reports import EquipmentInput, ReportCreateRequest
from app.services.report_service import ReportService, ReportValidationError


@pytest.mark.asyncio
async def test_equipment_type_has_default_unit(async_session):
    unit = Unit(code="m3", name="кубометр", symbol="м³", active=True)
    async_session.add(unit)
    await async_session.flush()

    eq = EquipmentType(code="EXC", name="Экскаватор", default_unit_id=unit.id, active=True)
    async_session.add(eq)
    await async_session.commit()

    result = await async_session.execute(select(EquipmentType).where(EquipmentType.id == eq.id))
    loaded = result.scalar_one()
    assert loaded.default_unit_id == unit.id


@pytest.mark.asyncio
async def test_work_type_has_default_unit(async_session):
    unit = Unit(code="hr", name="час", symbol="ч", active=True)
    async_session.add(unit)
    await async_session.flush()

    wt = WorkType(code="DIG", name="Земляные работы", default_unit_id=unit.id, active=True)
    async_session.add(wt)
    await async_session.commit()

    result = await async_session.execute(select(WorkType).where(WorkType.id == wt.id))
    loaded = result.scalar_one()
    assert loaded.default_unit_id == unit.id


@pytest.mark.asyncio
async def test_unit_validated_on_report_create(async_session):
    user = User(max_user_id="max-u1", full_name="Test", role="responsible")
    obj = Object(code="OBJ-U", name="Obj", active=True)
    stage = Stage(code="STG-U", name="Stage", active=True)
    unit = Unit(code="m3", name="кубометр", symbol="м³", active=True)
    eq_type = EquipmentType(code="EXC", name="Экскаватор", active=True)
    async_session.add_all([user, obj, stage, unit, eq_type])
    await async_session.flush()
    async_session.add(ObjectStage(object_id=obj.id, stage_id=stage.id))
    async_session.add(ResponsibleObjectAssignment(
        user_id=user.id, object_id=obj.id,
        active_from=date(2026, 1, 1), active_to=date(2026, 12, 31),
        schedule_type="daily",
    ))
    await async_session.commit()

    data = ReportCreateRequest(
        report_date=date(2026, 7, 15),
        object_id=obj.id,
        stage_id=stage.id,
        equipment=[EquipmentInput(
            equipment_type_id=eq_type.id,
            ownership="own",
            unit_id=unit.id,
            quantity=10,
        )],
    )
    service = ReportService(async_session)
    report = await service.create(user, data, "idem-u1")
    assert report.id is not None


@pytest.mark.asyncio
async def test_invalid_unit_rejected(async_session):
    user = User(max_user_id="max-u2", full_name="Test2", role="responsible")
    obj = Object(code="OBJ-U2", name="Obj2", active=True)
    stage = Stage(code="STG-U2", name="Stage2", active=True)
    eq_type = EquipmentType(code="EXC2", name="Экскаватор2", active=True)
    async_session.add_all([user, obj, stage, eq_type])
    await async_session.flush()
    async_session.add(ObjectStage(object_id=obj.id, stage_id=stage.id))
    async_session.add(ResponsibleObjectAssignment(
        user_id=user.id, object_id=obj.id,
        active_from=date(2026, 1, 1), active_to=date(2026, 12, 31),
        schedule_type="daily",
    ))
    await async_session.commit()

    data = ReportCreateRequest(
        report_date=date(2026, 7, 15),
        object_id=obj.id,
        stage_id=stage.id,
        equipment=[EquipmentInput(
            equipment_type_id=eq_type.id,
            ownership="own",
            unit_id=99999,
            quantity=10,
        )],
    )
    service = ReportService(async_session)
    with pytest.raises(ReportValidationError, match="unit not found"):
        await service.create(user, data, "idem-u2")
