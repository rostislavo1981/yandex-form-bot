"""Yandex Disk REST client with auto-refresh OAuth.

Endpoints (all https://cloud-api.yandex.net/v1/disk):
- GET /v1/disk/resources/upload?path=…  → {href, method}
- PUT  href                              → upload file body
- PUT  /v1/disk/resources?path=…        → create folder (idempotent: 409 = exists)

OAuth:
- yandex_disk_oauth_token: short-lived access token (default 1 year for services)
- On 401: refresh via https://oauth.yandex.ru/token (grant_type=refresh_token)
"""
from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

YANDEX_DISK_API = "https://cloud-api.yandex.net/v1/disk"
YANDEX_OAUTH_URL = "https://oauth.yandex.ru/token"


class DiskAuthError(RuntimeError):
    """Cannot authenticate to Yandex Disk."""


class DiskError(RuntimeError):
    """Yandex Disk API returned an error."""


class YandexDiskClient:
    """Async Yandex Disk client with auto-refresh on 401."""

    def __init__(
        self,
        oauth_token: str,
        refresh_token: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        if not oauth_token:
            raise ValueError("oauth_token is required")
        self._initial_token = oauth_token
        self._access_token: str = oauth_token
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        self._refresh_lock = asyncio.Lock()
        self._last_refresh: float = 0.0
        self._client = httpx.AsyncClient(
            base_url=YANDEX_DISK_API,
            headers={"Authorization": f"OAuth {oauth_token}"},
            timeout=timeout,
        )

    @property
    def access_token(self) -> str:
        return self._access_token

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> YandexDiskClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    async def _refresh_access_token(self) -> None:
        """Swap the access token using refresh_token. No-op if config missing."""
        if not (self.refresh_token and self.client_id and self.client_secret):
            raise DiskAuthError(
                "Cannot refresh: refresh_token/client_id/client_secret not configured"
            )
        async with self._refresh_lock:
            # Double-check inside lock (another coroutine may have refreshed)
            now = time.time()
            if now - self._last_refresh < 5:
                return
            try:
                resp = await self._client.post(
                    YANDEX_OAUTH_URL,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": self.refresh_token,
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    },
                )
            except httpx.HTTPError as e:
                raise DiskAuthError(f"transport error during refresh: {e}") from e
            if resp.status_code != 200:
                raise DiskAuthError(
                    f"refresh failed: {resp.status_code} {resp.text[:200]}"
                )
            data = resp.json()
            new_token = data.get("access_token")
            if not new_token:
                raise DiskAuthError(f"no access_token in response: {data}")
            self._access_token = new_token
            self._client.headers["Authorization"] = f"OAuth {new_token}"
            self._last_refresh = now
            # If a new refresh_token was issued, remember it
            if data.get("refresh_token"):
                self.refresh_token = data["refresh_token"]
            logger.info("YandexDisk: access token refreshed")

    async def request(
        self,
        method: str,
        path_or_url: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: bytes | None = None,
        allow_refresh: bool = True,
    ) -> httpx.Response:
        """Issue a request; on 401, refresh once and retry.

        For external URLs (e.g. upload href from Disk), pass full URL — httpx
        respects absolute URLs even with a base_url set.
        For Disk API paths, pass path starting with '/'.
        """
        resp = await self._client.request(
            method, path_or_url, params=params, json=json, content=data
        )

        if resp.status_code == 401 and allow_refresh:
            logger.info("YandexDisk: 401, refreshing token and retrying")
            await self._refresh_access_token()
            resp = await self._client.request(
                method, path_or_url, params=params, json=json, content=data
            )
        return resp

    # === High-level helpers ===============================================

    async def ensure_folder(self, path: str) -> bool:
        """Create folder at path. Idempotent: 201 = created, 409 = exists, 200 = updated."""
        # Normalize: must start with '/'
        norm = path if path.startswith("/") else f"/{path}"
        resp = await self.request("PUT", "/resources", params={"path": norm})
        if resp.status_code in (201, 200):
            return True
        if resp.status_code == 409:
            return False  # already exists
        if resp.status_code == 401:
            raise DiskAuthError(f"auth failed creating folder {norm!r}: {resp.text[:200]}")
        raise DiskError(f"ensure_folder({norm}) failed: {resp.status_code} {resp.text[:200]}")

    async def upload_file(self, remote_path: str, local_path: Path) -> str:
        """Upload a local file to remote_path. Returns the public URL (or '' if unpublished)."""
        # Normalize remote path
        norm = remote_path if remote_path.startswith("/") else f"/{remote_path}"
        # 1) Get upload href
        resp = await self.request(
            "GET", "/resources/upload", params={"path": norm, "overwrite": "true"}
        )
        if resp.status_code != 200:
            raise DiskError(
                f"get upload href failed: {resp.status_code} {resp.text[:200]}"
            )
        href = resp.json().get("href")
        if not href:
            raise DiskError(f"no href in upload response: {resp.text[:200]}")
        # 2) PUT file body
        data = local_path.read_bytes()
        resp2 = await self.request("PUT", href, data=data)
        if resp2.status_code not in (201, 200):
            raise DiskError(
                f"upload failed: {resp2.status_code} {resp2.text[:200]}"
            )
        # 3) Build public-ish URL (works if folder is published; else Disk file viewer URL)
        return f"https://disk.yandex.ru/client/disk{norm}"

    async def publish_link(self, remote_path: str) -> str | None:
        """Publish a file/folder and return its public URL. None on failure."""
        norm = remote_path if remote_path.startswith("/") else f"/{remote_path}"
        resp = await self.request("PUT", "/resources/publish", params={"path": norm})
        if resp.status_code != 200:
            logger.warning("publish_link(%s) failed: %s", norm, resp.status_code)
            return None
        return resp.json().get("public_url")
