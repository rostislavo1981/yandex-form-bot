from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session, require_user
from app.models.users import User
from app.schemas.reports import (
    ReportCreatedResponse,
    ReportCreateRequest,
    ReportDetailResponse,
    ReportListResponse,
    SubmissionStatusResponse,
)
from app.services.report_service import (
    ReportDuplicateError,
    ReportService,
    ReportValidationError,
)

router = APIRouter(
    prefix="/api/reports", tags=["reports"], dependencies=[Depends(require_user)]
)
submission_router = APIRouter(
    prefix="/api", tags=["submission"], dependencies=[Depends(require_user)]
)


def _extract_user(request: Request) -> User:
    """Return the user resolved by the require_user dependency."""
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user


@router.post("", response_model=ReportCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_report_endpoint(
    request: Request,
    data: ReportCreateRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_session),
) -> ReportCreatedResponse:
    """Submit a daily report for an object/stage."""
    from datetime import UTC, datetime

    from sqlalchemy import select

    from app.models.reports import ReportObligation

    user = _extract_user(request)
    service = ReportService(session)
    try:
        report = await service.create(user, data, idempotency_key)
    except ReportDuplicateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": str(exc)},
        ) from exc
    except ReportValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": str(exc)},
        ) from exc

    obligation_result = await session.execute(
        select(ReportObligation).where(ReportObligation.report_id == report.id)
    )
    due_at = getattr(obligation_result.scalar_one_or_none(), "due_at", None)
    late = due_at is not None and datetime.now(UTC) > due_at
    return ReportCreatedResponse(id=report.id, status=report.status, late=late)


@router.get("", response_model=ReportListResponse)
async def list_reports(
    request: Request,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    object_id: int | None = Query(None),
    responsible_user_id: int | None = Query(None),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> ReportListResponse:
    """List submitted reports with filters."""
    user = _extract_user(request)
    service = ReportService(session)
    items, total = await service.list_reports(
        user=user,
        date_from=date_from,
        date_to=date_to,
        object_id=object_id,
        responsible_user_id=responsible_user_id,
        limit=limit,
        offset=offset,
    )
    return ReportListResponse(
        items=[ReportDetailResponse.model_validate(item) for item in items],
        total=total,
    )


@router.get("/{report_id}", response_model=ReportDetailResponse)
async def get_report_detail(
    report_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> ReportDetailResponse:
    """Get full report details by id (responsible sees only own reports)."""
    from sqlalchemy import select

    from app.models.reports import DailyReport

    user = _extract_user(request)
    result = await session.execute(
        select(DailyReport).where(DailyReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="report not found",
        )
    if user.role == "responsible" and report.responsible_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к чужому отчёту",
        )
    return ReportDetailResponse.model_validate(report)


@submission_router.get("/submission-status", response_model=SubmissionStatusResponse)
async def submission_status(
    request: Request,
    target_date: date = Query(..., alias="date"),
    session: AsyncSession = Depends(get_session),
) -> SubmissionStatusResponse:
    """Return submission status for a given date."""
    user = _extract_user(request)
    service = ReportService(session)
    data = await service.submission_status(user, target_date)
    return SubmissionStatusResponse(**data)
