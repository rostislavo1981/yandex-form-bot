from __future__ import annotations

import hmac

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.users import User


async def get_session(session: AsyncSession = Depends(get_db)) -> AsyncSession:
    """FastAPI dependency alias for an async DB session."""
    return session


async def require_user(
    request: Request,
    x_init_data: str | None = Header(None, alias="X-Init-Data"),
) -> User:
    """Resolve the current user for any protected endpoint.

    Order: user already attached to request.state (dev middleware) →
    MAX initData from the X-Init-Data header. Stores the resolved user in
    request.state so endpoint-local helpers keep working.
    """
    user = getattr(request.state, "user", None)
    if user is None:
        from app.api.auth import resolve_user_from_init_data

        user = await resolve_user_from_init_data(x_init_data)
        request.state.user = user
    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь деактивирован",
        )
    return user


def require_roles(*roles: str):
    """Dependency factory: authenticated user with one of the given roles."""

    async def dependency(user: User = Depends(require_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав",
            )
        return user

    return dependency


require_manager = require_roles("manager", "admin")


async def require_internal(
    x_internal_token: str | None = Header(None, alias="X-Internal-Token"),
) -> None:
    """Guard for internal endpoints (scheduler/worker).

    If INTERNAL_TOKEN is configured — header must match.
    If not configured — access is allowed only in dev mode.
    """
    if settings.internal_token:
        if not x_internal_token or not hmac.compare_digest(
            x_internal_token, settings.internal_token
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid internal token",
            )
        return
    if settings.app_env != "dev":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Internal token not configured",
        )
