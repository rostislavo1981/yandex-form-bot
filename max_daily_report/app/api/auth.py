from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import parse_qsl

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.users import User
from app.schemas.users import UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])

INIT_DATA_TTL_SECONDS = 3600


class AuthResponse(BaseModel):
    user: UserResponse


class InitDataPayload(BaseModel):
    init_data: str


def _parse_init_data(raw: str) -> dict[str, str]:
    """Parse initData query string and reject if multiple hashes are present."""
    parsed: dict[str, str] = {}
    hash_count = 0
    for key, value in parse_qsl(raw, keep_blank_values=True):
        if key == "hash":
            hash_count += 1
        parsed[key] = value
    if hash_count != 1:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid initData: hash count",
        )
    return parsed


def _validate_init_data(raw: str) -> dict[str, str]:
    """Verify MAX WebApp initData HMAC signature and auth_date TTL."""
    if not settings.max_bot_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="bot token not configured",
        )

    data = _parse_init_data(raw)
    received_hash = data.pop("hash")

    # parse_qsl уже URL-декодировал значения — повторный unquote исказил бы
    # строки, содержащие %-последовательности (двойное декодирование)
    params = [f"{k}={v}" for k, v in sorted(data.items())]
    launch_params = "\n".join(params)

    secret_key = hmac.new(
        b"WebAppData",
        settings.max_bot_token.encode(),
        hashlib.sha256,
    ).digest()
    expected_hash = hmac.new(
        secret_key,
        launch_params.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid initData signature",
        )

    auth_date = int(data.get("auth_date", "0"))
    now = int(time.time())
    if now - auth_date > INIT_DATA_TTL_SECONDS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="initData expired",
        )

    return data


async def _dev_fallback_user() -> User:
    """Return or create a dev placeholder user; disabled unless DEBUG is true."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.max_user_id == "dev-user")
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                max_user_id="dev-user",
                full_name="Dev User",
                role="responsible",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user


async def resolve_user_from_init_data(init_data: str | None) -> User:
    """Resolve a User from initData or dev fallback."""
    if init_data == "dev":
        # Gate strictly on APP_ENV: DEBUG=true must never open dev auth in prod.
        if settings.app_env != "dev":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="dev auth disabled",
            )
        return await _dev_fallback_user()

    if not init_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="initData required",
        )

    data = _validate_init_data(init_data)
    user_json = data.get("user", "{}")
    import json

    try:
        user_info = json.loads(user_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid user payload",
        ) from exc

    raw_user_id = user_info.get("id")
    if raw_user_id is None or raw_user_id == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="user id missing",
        )
    max_user_id = str(raw_user_id)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.max_user_id == max_user_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="user not registered",
            )
        return user


@router.get("/me", response_model=AuthResponse)
async def me(
    request: Request,
    x_init_data: str | None = Header(None, alias="X-Init-Data"),
    x_admin_password: str | None = Header(None, alias="X-Admin-Password"),
) -> AuthResponse:
    """Return current user authenticated by MAX initData."""
    # In dev mode the dev-only middleware may have already attached a user.
    state_user = getattr(request.state, "user", None)
    if state_user is not None:
        return AuthResponse(user=UserResponse.model_validate(state_user))

    # Admin password bypass for browser access without MAX.
    if (
        x_admin_password
        and settings.admin_password
        and hmac.compare_digest(x_admin_password, settings.admin_password)
    ):
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select

            admin_user = (
                await session.execute(
                    select(User).where(User.role.in_(["admin", "manager"])).order_by(User.id)
                )
            ).scalars().first()
            if admin_user is None:
                admin_user = (
                    await session.execute(select(User).order_by(User.id))
                ).scalars().first()
            if admin_user is not None:
                return AuthResponse(user=UserResponse.model_validate(admin_user))

    if not x_init_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="initData required",
        )

    user = await resolve_user_from_init_data(x_init_data)
    return AuthResponse(user=UserResponse.model_validate(user))
