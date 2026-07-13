from __future__ import annotations

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.config import settings

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
