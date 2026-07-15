from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session, require_internal
from app.services.scheduler_service import SchedulerService, advisory_lock

router = APIRouter(
    prefix="/api/scheduler",
    tags=["scheduler"],
    dependencies=[Depends(require_internal)],
)


@router.post("/morning")
async def run_morning(
    session: AsyncSession = Depends(get_session),
    target_date: date | None = Query(None),
) -> dict[str, int]:
    async with advisory_lock(1001) as acquired:
        if not acquired:
            raise HTTPException(status_code=409, detail="scheduler already running")
        service = SchedulerService(session)
        return await service.run_morning(target_date)


@router.post("/evening-reminder")
async def run_evening_reminder(
    group_id: int = Query(...),
    reminder_number: int = Query(..., ge=1, le=2),
    target_date: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    async with advisory_lock(2000 + reminder_number) as acquired:
        if not acquired:
            raise HTTPException(status_code=409, detail="reminder already running")
        service = SchedulerService(session)
        return await service.run_evening_reminder(group_id, reminder_number, target_date)


@router.post("/morning-summary")
async def run_morning_summary(
    group_id: int = Query(...),
    target_date: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    async with advisory_lock(3000) as acquired:
        if not acquired:
            raise HTTPException(status_code=409, detail="morning summary already running")
        service = SchedulerService(session)
        return await service.run_morning_summary(group_id, target_date)
