"""MAX (mail.ru) bot client.

Telegram Bot API compatible. Same method names + JSON shapes:
  /bot<token>/getUpdates
  /bot<token>/sendMessage
  /bot<token>/sendDocument (for /summary)

If the actual MAX API differs, override MAX_API_BASE in env.

If the platform doesn't implement getUpdates/sendMessage this way,
the test suite will catch it at integration time.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_MAX_API_BASE = "https://botapi.max.ru"


class MaxClient:
    """Thin async client. One instance per bot process."""

    def __init__(
        self,
        token: str,
        *,
        base_url: str = DEFAULT_MAX_API_BASE,
        timeout: float = 30.0,
    ) -> None:
        if not token:
            raise ValueError("token is required")
        self._token = token
        self._base = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout)

    @property
    def token(self) -> str:
        return self._token

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> MaxClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    async def _call(self, method: str, **params: Any) -> dict:
        url = f"{self._base}/bot{self._token}/{method}"
        try:
            resp = await self._client.post(url, json=params)
        except httpx.HTTPError as e:
            raise MaxError(f"transport error: {e}") from e
        try:
            data = resp.json()
        except json.JSONDecodeError as e:
            raise MaxError(f"non-JSON response: {resp.text[:200]}") from e
        if not data.get("ok", False):
            raise MaxError(f"{method} failed: {data}")
        return data

    async def get_updates(
        self, offset: int | None = None, timeout: int = 25
    ) -> list[dict]:
        params: dict[str, Any] = {"timeout": timeout, "allowed_updates": ["message"]}
        if offset is not None:
            params["offset"] = offset
        data = await self._call("getUpdates", **params)
        return data.get("result", [])

    async def send_message(self, chat_id: int | str, text: str) -> dict:
        # Telegram caps message text at 4096 chars; trim if longer
        if len(text) > 4000:
            text = text[:3997] + "..."
        return await self._call("sendMessage", chat_id=str(chat_id), text=text)

    async def send_document(
        self, chat_id: int | str, document_path: str, caption: str | None = None
    ) -> dict:
        """Send a file (e.g. .xlsx) by path. Uses multipart upload."""
        url = f"{self._base}/bot{self._token}/sendDocument"
        with open(document_path, "rb") as f:
            files = {"document": f}
            data: dict[str, Any] = {"chat_id": str(chat_id)}
            if caption:
                data["caption"] = caption
            try:
                resp = await self._client.post(url, data=data, files=files)
            except httpx.HTTPError as e:
                raise MaxError(f"transport error: {e}") from e
        try:
            payload = resp.json()
        except json.JSONDecodeError as e:
            raise MaxError(f"non-JSON response: {resp.text[:200]}") from e
        if not payload.get("ok", False):
            raise MaxError(f"sendDocument failed: {payload}")
        return payload


class MaxError(RuntimeError):
    """Raised on MAX API failure."""
