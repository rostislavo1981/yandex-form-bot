"""Real Playwright (sync_api wrapped in asyncio.to_thread) implementation.

Imported lazily — requires `playwright install chromium` to actually run.
For tests use FakePlaywrightClient from backend.forms.

Why sync API inside asyncio.to_thread:
- playwright's async API still requires the same event-loop dance.
- sync API is the officially blessed path for one-off scripts.
- Running sync in a worker thread keeps the bot's event loop unblocked.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from backend.forms import FormFillError

logger = logging.getLogger(__name__)


class RealPlaywrightClient:
    """Headless Chromium driver. Use as `async with RealPlaywrightClient() as c:`."""

    def __init__(
        self,
        *,
        headless: bool = True,
        user_data_dir: Path | None = None,
        timeout_ms: int = 15_000,
    ) -> None:
        # Importing playwright at top-level would force users without the
        # `playwright` extra to install it. Lazy-import here.
        from playwright.sync_api import (  # type: ignore[import-untyped]
            sync_playwright,
        )

        self._sync_playwright = sync_playwright
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None
        self._headless = headless
        self._user_data_dir = user_data_dir
        self._timeout_ms = timeout_ms

    async def __aenter__(self) -> RealPlaywrightClient:
        await self._start()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def _start(self) -> None:
        def _launch() -> None:
            self._pw = self._sync_playwright().start()
            kwargs: dict[str, object] = {"headless": self._headless}
            if self._user_data_dir:
                # persistent context keeps cookies between runs
                self._context = self._pw.chromium.launch_persistent_context(
                    str(self._user_data_dir), **kwargs
                )
            else:
                self._browser = self._pw.chromium.launch(**kwargs)
                self._context = self._browser.new_context()
            self._page = self._context.new_page()
            self._page.set_default_timeout(self._timeout_ms)

        await asyncio.to_thread(_launch)
        logger.info("RealPlaywright: chromium launched (headless=%s)", self._headless)

    async def goto(self, url: str) -> None:
        def _g() -> None:
            assert self._page is not None
            self._page.goto(url)

        try:
            await asyncio.to_thread(_g)
        except Exception as e:
            raise FormFillError(f"goto({url}) failed: {e}") from e

    async def fill(self, selector: str, value: str) -> None:
        def _f() -> None:
            assert self._page is not None
            # str(value) — never let None become "None"
            v = str(value) if value is not None else ""
            self._page.fill(selector, v)

        try:
            await asyncio.to_thread(_f)
        except Exception as e:
            raise FormFillError(f"fill({selector}) failed: {e}") from e

    async def submit(self) -> None:
        def _s() -> None:
            assert self._page is not None
            # Heuristic: any submit button. Real selectors will be refined.
            btn = self._page.locator('button[type="submit"], input[type="submit"]').first
            btn.click()

        try:
            await asyncio.to_thread(_s)
        except Exception as e:
            raise FormFillError(f"submit failed: {e}") from e

    async def screenshot(self, path: Path) -> Path:
        def _s() -> None:
            assert self._page is not None
            path.parent.mkdir(parents=True, exist_ok=True)
            self._page.screenshot(path=str(path))

        try:
            await asyncio.to_thread(_s)
        except Exception as e:
            raise FormFillError(f"screenshot({path}) failed: {e}") from e
        return path

    async def close(self) -> None:
        def _c() -> None:
            try:
                if self._context:
                    self._context.close()
                if self._browser:
                    self._browser.close()
                if self._pw:
                    self._pw.stop()
            except Exception:  # noqa: BLE001 — best-effort shutdown
                pass

        await asyncio.to_thread(_c)
