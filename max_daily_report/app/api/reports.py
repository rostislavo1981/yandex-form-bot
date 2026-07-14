from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session
from app.models.users import User
from app.schemas.reports import (
    ReportCreatedResponse,
    ReportCreateRequest,
    ReportDetailResponse,
)
from app.services.report_service import ReportService, ReportValidationError

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _extract_user(request: Request) -> User:
    """Dev-only auth: attach placeholder user stored in app state."""
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
    user = _extract_user(request)
    service = ReportService(session)
    try:
        report = await service.create(user, data, idempotency_key)
    except ReportValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": str(exc)},
        ) from exc
    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    due_at = getattr(
        (
            await session.execute(
                __import__("sqlalchemy", fromlist=["select"]).select(
                    __import__("app.models.reports", fromlist=["ReportObligation"]).ReportObligation
                ).where(
                    __import__("app.models.reports", fromlist=["ReportObligation"]).ReportObligation.report_id
                    == report.id
                )
            )
        ).scalar_one_or_none(),
        "due_at",
        None,
    )
    late = due_at is not None and now > due_at
    return ReportCreatedResponse(id=report.id, status=report.status, late=late)


@router.get("/{report_id}", response_model=ReportDetailResponse)
async def get_report_detail(
    report_id: int,
    session: AsyncSession = Depends(get_session),
) -> ReportDetailResponse:
    """Get full report details by id."""
    from sqlalchemy import select

    from app.models.reports import DailyReport

    result = await session.execute(
        select(DailyReport).where(DailyReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="report not found",
        )
    return ReportDetailResponse.model_validate(report)
