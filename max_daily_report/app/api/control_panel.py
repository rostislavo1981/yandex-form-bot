from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session, require_user
from app.models.users import User
from app.services.control_panel_service import ControlPanelService

router = APIRouter(
    prefix="/api/control-panel",
    tags=["control-panel"],
    dependencies=[Depends(require_user)],
)


def _extract_user(request: Request) -> User:
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user


def _require_role(user: User, allowed: set[str]) -> None:
    if user.role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="insufficient role",
        )


@router.post("/group/{group_id}/ensure", response_model=dict[str, Any])
async def ensure_group_panel(
    group_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    user = _extract_user(request)
    _require_role(user, {"manager", "admin"})
    service = ControlPanelService(session)
    return await service.ensure_group_control_panel(group_id)


@router.post("/private/ensure", response_model=dict[str, Any])
async def ensure_private_panel(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    user = _extract_user(request)
    _require_role(user, {"responsible", "manager", "admin"})
    service = ControlPanelService(session)
    return await service.ensure_private_control_panel(user.id)


@router.post("/group/{group_id}/refresh", response_model=dict[str, str])
async def refresh_group_panel(
    group_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    user = _extract_user(request)
    _require_role(user, {"manager", "admin"})
    service = ControlPanelService(session)
    await service.refresh_group_panel_outbox(group_id, actor_user_id=user.id)
    await session.commit()
    return {"status": "scheduled"}


@router.post("/private/refresh", response_model=dict[str, str])
async def refresh_private_panel(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    user = _extract_user(request)
    _require_role(user, {"responsible", "manager", "admin"})
    service = ControlPanelService(session)
    await service.ensure_private_control_panel(user.id)
    return {"status": "ok"}
