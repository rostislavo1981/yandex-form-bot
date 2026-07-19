from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db

router = APIRouter(prefix="/api", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health() -> HealthResponse:
    """Public health-check endpoint used by Docker and monitoring."""
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        version=settings.version,
    )


@router.get("/ready", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def readiness(
    session: AsyncSession = Depends(get_db),
) -> HealthResponse:
    """Readiness probe: the process is ready only when PostgreSQL responds."""
    await session.execute(text("SELECT 1"))
    return HealthResponse(
        status="ready",
        app_name=settings.app_name,
        version=settings.version,
    )
