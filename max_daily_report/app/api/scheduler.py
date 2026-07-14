from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session, require_internal
from app.services.scheduler_service import SchedulerService

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
    service = SchedulerService(session)
    lock_acquired = await service.acquire_lock(1001)
    if not lock_acquired:
        raise HTTPException(status_code=409, detail="scheduler already running")
    try:
        return await service.run_morning(target_date)
    finally:
        await service.release_lock(1001)


@router.post("/evening-reminder")
async def run_evening_reminder(
    group_id: int = Query(...),
    reminder_number: int = Query(..., ge=1, le=2),
    target_date: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    service = SchedulerService(session)
    lock_id = 2000 + reminder_number
    lock_acquired = await service.acquire_lock(lock_id)
    if not lock_acquired:
        raise HTTPException(status_code=409, detail="reminder already running")
    try:
        return await service.run_evening_reminder(group_id, reminder_number, target_date)
    finally:
        await service.release_lock(lock_id)


@router.post("/morning-summary")
async def run_morning_summary(
    group_id: int = Query(...),
    target_date: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    service = SchedulerService(session)
    lock_id = 3000
    lock_acquired = await service.acquire_lock(lock_id)
    if not lock_acquired:
        raise HTTPException(status_code=409, detail="morning summary already running")
    try:
        return await service.run_morning_summary(group_id, target_date)
    finally:
        await service.release_lock(lock_id)
