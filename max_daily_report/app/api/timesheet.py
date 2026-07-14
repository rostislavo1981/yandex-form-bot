from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session
from app.models.users import User
from app.services.timesheet_excel_service import TimesheetExcelBuilder
from app.services.timesheet_service import TimesheetService

router = APIRouter(prefix="/api/timesheet", tags=["timesheet"])


def _extract_user(request: Request) -> User:
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user


@router.get("/{object_id}")
async def get_timesheet(
    object_id: int,
    date_from: date,
    date_to: date,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    user = _extract_user(request)
    # responsible can only view objects assigned to them
    if user.role == "responsible":
        from sqlalchemy import select

        from app.models.reports import ResponsibleObjectAssignment

        result = await session.execute(
            select(ResponsibleObjectAssignment).where(
                ResponsibleObjectAssignment.user_id == user.id,
                ResponsibleObjectAssignment.object_id == object_id,
                ResponsibleObjectAssignment.active.is_(True),
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="object not assigned",
            )

    service = TimesheetService(session)
    try:
        return await service.build(object_id, date_from, date_to)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get("/{object_id}/export.xlsx")
async def export_timesheet(
    object_id: int,
    date_from: date = Query(...),
    date_to: date = Query(...),
    request: Request = None,
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    user = _extract_user(request)
    if user.role == "responsible":
        from sqlalchemy import select

        from app.models.reports import ResponsibleObjectAssignment

        result = await session.execute(
            select(ResponsibleObjectAssignment).where(
                ResponsibleObjectAssignment.user_id == user.id,
                ResponsibleObjectAssignment.object_id == object_id,
                ResponsibleObjectAssignment.active.is_(True),
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="object not assigned",
            )

    service = TimesheetService(session)
    builder = TimesheetExcelBuilder(service)
    buffer = await builder.build_for_object(object_id, date_from, date_to)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=timesheet_{object_id}_{date_from}_{date_to}.xlsx"
        },
    )
