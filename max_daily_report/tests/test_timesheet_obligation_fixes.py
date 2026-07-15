"""F4 regression tests: timesheet accumulation, obligations period, late."""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from app.database import AsyncSessionLocal
from app.models.catalogs import Object, ObjectStage, Stage, Unit
from app.models.reports import (
    DailyReport,
    ReportObligation,
    ResponsibleObjectAssignment,
)
from app.models.users import User
from app.schemas.reports import ReportCreateRequest
from app.services.obligation_service import generate_obligations
from app.services.report_service import ReportService
from app.services.timesheet_service import TimesheetService


@pytest.fixture
def base_data(db_session):
    user_a = User(max_user_id="f4-a", full_name="Один", role="responsible")
    user_b = User(max_user_id="f4-b", full_name="Два", role="responsible")
    unit = Unit(code="h-f4", name="час", symbol="ч")
    obj = Object(code="obj-f4", name="Объект F4", execution_method="own")
    stage = Stage(code="st-f4", name="Этап F4")
    db_session.add_all([user_a, user_b, unit, obj, stage])
    db_session.flush()
    db_session.add(ObjectStage(object_id=obj.id, stage_id=stage.id))
    for user in (user_a, user_b):
        db_session.add(
            ResponsibleObjectAssignment(
                user_id=user.id,
                object_id=obj.id,
                active_from=date(2026, 1, 1),
                active_to=date(2026, 12, 31),
                schedule_type="daily",
            )
        )
    db_session.commit()
    return {
        "user_a_id": user_a.id,
        "user_b_id": user_b.id,
        "obj_id": obj.id,
        "stage_id": stage.id,
        "unit_id": unit.id,
    }


async def _create_report(user_id: int, data: dict, key: str) -> None:
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        service = ReportService(session)
        await service.create(user, ReportCreateRequest(**data), key)


@pytest.mark.asyncio
async def test_personnel_and_soil_accumulate_across_reports(base_data):
    """F4.1: два отчёта одного дня — персонал и грунт суммируются."""
    report_date = date(2026, 7, 14)
    payload = {
        "report_date": report_date,
        "object_id": base_data["obj_id"],
        "stage_id": base_data["stage_id"],
        "staff": {"itr": 1, "internal": 2, "external": 0},
        "soil_export_m3": "10.00",
    }
    await _create_report(base_data["user_a_id"], payload, "f4-acc-1")
    payload_b = dict(payload, staff={"itr": 0, "internal": 3, "external": 1})
    payload_b["soil_export_m3"] = "5.50"
    await _create_report(base_data["user_b_id"], payload_b, "f4-acc-2")

    async with AsyncSessionLocal() as session:
        service = TimesheetService(session)
        sheet = await service.build(base_data["obj_id"], report_date, report_date)

    personnel = next(r for r in sheet["rows"] if r["category"] == "personnel")
    soil = next(r for r in sheet["rows"] if r["category"] == "soil")
    assert personnel["values"][0] == "7"  # 3 + 4 человека
    assert soil["values"][0] == "15.5"  # 10 + 5.5


@pytest.mark.asyncio
async def test_average_uses_expected_days(base_data):
    """F4.2: среднее делится на дни, где ожидался отчёт, а не на дни с данными."""
    d1 = date(2026, 7, 13)
    d2 = date(2026, 7, 14)
    async with AsyncSessionLocal() as session:
        await generate_obligations(session, d1, d2)

    payload = {
        "report_date": d2,
        "object_id": base_data["obj_id"],
        "stage_id": base_data["stage_id"],
        "staff": {"itr": 4, "internal": 0, "external": 0},
    }
    await _create_report(base_data["user_a_id"], payload, "f4-avg-1")

    async with AsyncSessionLocal() as session:
        service = TimesheetService(session)
        sheet = await service.build(base_data["obj_id"], d1, d2)

    personnel = next(r for r in sheet["rows"] if r["category"] == "personnel")
    # total 4, expected 2 дня → среднее 2, а не 4
    assert personnel["total"] == "4"
    assert personnel["average"] == "2"


@pytest.mark.asyncio
async def test_obligations_respect_assignment_period(db_session):
    """F4.3: истёкшее назначение не порождает обязательств."""
    user = User(max_user_id="f4-exp", full_name="Истёкший", role="responsible")
    obj = Object(code="obj-f4-exp", name="Объект", execution_method="own")
    db_session.add_all([user, obj])
    db_session.flush()
    db_session.add(
        ResponsibleObjectAssignment(
            user_id=user.id,
            object_id=obj.id,
            active_from=date(2026, 1, 1),
            active_to=date(2026, 6, 30),  # закончилось в июне
            schedule_type="daily",
        )
    )
    db_session.commit()

    async with AsyncSessionLocal() as session:
        created, _skipped = await generate_obligations(
            session, date(2026, 7, 14), date(2026, 7, 14)
        )
    assert created == 0


@pytest.mark.asyncio
async def test_late_submission_sets_late_status(base_data, db_session):
    """F4.4: сдача после due_at помечает обязательство как late."""
    report_date = date(2026, 7, 10)
    async with AsyncSessionLocal() as session:
        await generate_obligations(session, report_date, report_date)
        # сдвигаем дедлайн в прошлое
        from sqlalchemy import update

        await session.execute(
            update(ReportObligation)
            .where(ReportObligation.report_date == report_date)
            .values(due_at=datetime.now(UTC) - timedelta(days=1))
        )
        await session.commit()

    payload = {
        "report_date": report_date,
        "object_id": base_data["obj_id"],
        "stage_id": base_data["stage_id"],
        "staff": {"itr": 1, "internal": 0, "external": 0},
    }
    await _create_report(base_data["user_a_id"], payload, "f4-late-1")

    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(ReportObligation).where(
                ReportObligation.report_date == report_date,
                ReportObligation.user_id == base_data["user_a_id"],
            )
        )
        obligation = result.scalar_one()
        assert obligation.status == "late"
        assert obligation.report_id is not None


@pytest.mark.asyncio
async def test_due_at_is_timezone_aware(db_session):
    """F4.5: due_at — конец дня по Москве, tz-aware."""
    from app.services.obligation_service import _due_at_for_date

    due = _due_at_for_date(date(2026, 7, 14))
    assert due.tzinfo is not None
    assert due.hour == 23
    # 23:59:59 MSK == 20:59:59 UTC
    assert due.astimezone(UTC).hour == 20


@pytest.mark.asyncio
async def test_second_report_same_day_now_blocked(base_data):
    """После F3.4/F4: у одного пользователя второй отчёт за день — ошибка дубля."""
    from app.services.report_service import ReportDuplicateError

    report_date = date(2026, 7, 15)
    payload = {
        "report_date": report_date,
        "object_id": base_data["obj_id"],
        "stage_id": base_data["stage_id"],
        "staff": {"itr": 1, "internal": 0, "external": 0},
    }
    await _create_report(base_data["user_a_id"], payload, "f4-dup-1")
    with pytest.raises(ReportDuplicateError):
        await _create_report(base_data["user_a_id"], payload, "f4-dup-2")


@pytest.mark.asyncio
async def test_reports_from_two_users_one_object_both_stored(base_data):
    """Контроль: отчёты разных пользователей по одному объекту не конфликтуют."""
    report_date = date(2026, 7, 16)
    payload = {
        "report_date": report_date,
        "object_id": base_data["obj_id"],
        "stage_id": base_data["stage_id"],
        "staff": {"itr": 1, "internal": 0, "external": 0},
    }
    await _create_report(base_data["user_a_id"], payload, "f4-two-1")
    await _create_report(base_data["user_b_id"], payload, "f4-two-2")

    async with AsyncSessionLocal() as session:
        from sqlalchemy import func, select

        count = await session.scalar(
            select(func.count()).select_from(DailyReport).where(
                DailyReport.report_date == report_date
            )
        )
        assert count == 2
