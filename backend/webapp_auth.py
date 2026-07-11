"""HMAC verification of MAX Mini App initData.

MAX (mail.ru) WebApp initData format (Telegram-compatible):
  query_id=...&user=...&auth_date=...&hash=...

Hash is computed over the URL-encoded key=value pairs (sorted, excluding hash)
using secret = SHA256(MAX_BOT_TOKEN).

If signature is valid, we trust `user.id`, `user.first_name`, etc.
If invalid (or absent), we reject with 401.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any
from urllib.parse import parse_qsl, urlencode

from fastapi import Header, HTTPException, status

logger = logging.getLogger(__name__)

AUTH_TTL_SECONDS = 24 * 3600  # initData older than this -> reject


def _secret_key(bot_token: str) -> bytes:
    """MAX WebApp secret = SHA256(bot_token) (Telegram convention)."""
    return hashlib.sha256(bot_token.encode("utf-8")).digest()


def verify_init_data(
    init_data: str, bot_token: str, *, max_age_seconds: int = AUTH_TTL_SECONDS
) -> dict[str, Any]:
    """Parse and verify initData from a MAX Mini App.

    Returns the parsed dict (includes `user` dict, `auth_date`, etc.).
    Raises HTTPException(401) on bad signature or expired auth.
    """
    if not init_data:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing initData")
    if not bot_token:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "MAX_BOT_TOKEN not configured"
        )

    # Parse
    pairs = parse_qsl(init_data, keep_blank_values=True)
    data = dict(pairs)

    received_hash = data.pop("hash", "")
    if not received_hash:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing hash")

    # Check signature: build canonical string from sorted (k,v) pairs
    canonical = urlencode(sorted(data.items()))
    expected_hash = hmac.new(
        _secret_key(bot_token), canonical.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash):
        logger.warning("initData signature mismatch")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "bad signature")

    # Check auth_date (prevent replay)
    auth_date = int(data.get("auth_date", "0"))
    if not auth_date or (time.time() - auth_date) > max_age_seconds:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "initData expired")

    return data


async def require_webapp_user(
    x_auth_init_data: str | None = Header(default=None, alias="X-Auth-InitData"),
) -> dict[str, Any]:
    """FastAPI dependency: extract + verify initData header.

    Usage: @app.get("/api/...") , dependencies=[Depends(require_webapp_user)]
    """
    from backend.config import get_settings

    s = get_settings()
    if not x_auth_init_data:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "X-Auth-InitData required")
    return verify_init_data(x_auth_init_data, s.max_bot_token or "")
