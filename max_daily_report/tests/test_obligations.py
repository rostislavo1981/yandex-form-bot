from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.catalogs import Object
from app.models.reports import ReportObligation, ResponsibleObjectAssignment
from app.models.users import User
from app.services.obligation_service import generate_obligations


async def _seed_data(session, suffix: str):
    user = User(
        max_user_id=f"max-{suffix}", full_name=f"User {suffix}", role="responsible"
    )
    session.add(user)
    await session.flush()

    obj1 = Object(code=f"obj1-{suffix}", name="Object 1", execution_method="own")
    obj2 = Object(
        code=f"obj2-{suffix}", name="Object 2", execution_method="contractor"
    )
    obj3 = Object(code=f"obj3-{suffix}", name="Object 3", execution_method="own")
    session.add_all([obj1, obj2, obj3])
    await session.flush()

    assignments = []
    for idx, obj in enumerate([obj1, obj2, obj3]):
        schedule = "daily" if idx % 2 == 0 else "weekdays"
        assignment = ResponsibleObjectAssignment(
            user_id=user.id,
            object_id=obj.id,
            active_from=date(2026, 1, 1),
            active_to=date(2026, 12, 31),
            schedule_type=schedule,
        )
        session.add(assignment)
        assignments.append(assignment)
    await session.commit()
    return user, assignments


@pytest.mark.asyncio
async def test_generates_obligations_for_three_objects():
    suffix = "test-obl-1"
    async with AsyncSessionLocal() as session:
        user, _assignments = await _seed_data(session, suffix)

        start = date(2026, 7, 1)
        end = date(2026, 7, 3)
        created, skipped = await generate_obligations(session, start, end)

        assert created == 9

        result = await session.execute(
            select(ReportObligation).where(ReportObligation.user_id == user.id)
        )
        obligations = result.scalars().all()
        assert len(obligations) == 9
        object_ids = {o.object_id for o in obligations}
        assert len(object_ids) == 3


@pytest.mark.asyncio
async def test_weekdays_excludes_weekend():
    suffix = "test-obl-2"
    async with AsyncSessionLocal() as session:
        user, _assignments = await _seed_data(session, suffix)

        monday = date(2026, 7, 13)
        friday = date(2026, 7, 17)
        created, skipped = await generate_obligations(session, monday, friday)

        result = await session.execute(
            select(ReportObligation).where(ReportObligation.user_id == user.id)
        )
        obligations = result.scalars().all()
        dates = {o.report_date for o in obligations}
        assert date(2026, 7, 18) not in dates
        assert date(2026, 7, 19) not in dates


@pytest.mark.asyncio
async def test_idempotent_generation():
    suffix = "test-obl-3"
    async with AsyncSessionLocal() as session:
        user, _assignments = await _seed_data(session, suffix)

        start = date(2026, 7, 1)
        end = date(2026, 7, 3)
        created1, _ = await generate_obligations(session, start, end)
        created2, _ = await generate_obligations(session, start, end)

        assert created1 == 9
        assert created2 == 0

        result = await session.execute(
            select(ReportObligation).where(ReportObligation.user_id == user.id)
        )
        assert len(result.scalars().all()) == 9
