"""Abstract Playwright form-filler interface + a recording fake for tests.

Two implementations:
- `PlaywrightFormClient` (Protocol): the contract; production uses PlaywrightFormReal.
- `FakePlaywrightClient`: in-memory recorder. Tests assert on the call sequence.

We intentionally do NOT depend on `playwright` at import time. The real
implementation lives in `backend.forms.playwright_real` and is imported
lazily by the CLI; tests use the fake.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


class FormFillError(RuntimeError):
    """Raised when the form cannot be filled (selector not found, submit fails, etc.)."""


@dataclass
class FillRecord:
    """One call recorded by FakePlaywrightClient."""

    method: str
    args: tuple[Any, ...] = ()
    result: str = "ok"
    error: str | None = None


@runtime_checkable
class PlaywrightFormClient(Protocol):
    """Async form-filler. Methods raise FormFillError on failure."""

    async def goto(self, url: str) -> None: ...
    async def fill(self, selector: str, value: str) -> None: ...
    async def submit(self) -> None: ...
    async def screenshot(self, path: Path) -> Path: ...
    async def close(self) -> None: ...


class FakePlaywrightClient:
    """In-memory fake. Records every call; replays a sequence of (selector, value)
    pairs for `fill()`. Useful for golden tests and unit tests.

    Behavior knobs:
    - `selectors_not_found`: set of selectors that should raise FormFillError.
    - `submit_should_succeed`: bool (default True). If False, submit raises.
    - `records`: list of FillRecord written to.
    """

    def __init__(
        self,
        *,
        selectors_not_found: set[str] | None = None,
        submit_should_succeed: bool = True,
    ) -> None:
        self._selectors_not_found = selectors_not_found or set()
        self._submit_should_succeed = submit_should_succeed
        self.records: list[FillRecord] = []
        self.goto_url: str | None = None
        self.submitted = False
        self.screenshot_path: Path | None = None
        self.closed = False
        # Internal: filled values, for inspection
        self.filled: dict[str, str] = {}

    async def goto(self, url: str) -> None:
        self.records.append(FillRecord("goto", (url,)))
        self.goto_url = url
        logger.info("FakePlaywright: goto %s", url)

    async def fill(self, selector: str, value: str) -> None:
        self.records.append(FillRecord("fill", (selector, value)))
        if selector in self._selectors_not_found:
            err = f"selector not found: {selector}"
            self.records.append(FillRecord("fill", (selector, value), result="error", error=err))
            raise FormFillError(err)
        self.filled[selector] = value
        logger.info("FakePlaywright: fill %s = %r", selector, value)

    async def submit(self) -> None:
        self.records.append(FillRecord("submit"))
        if not self._submit_should_succeed:
            err = "submit failed (simulated)"
            self.records.append(FillRecord("submit", result="error", error=err))
            raise FormFillError(err)
        self.submitted = True

    async def screenshot(self, path: Path) -> Path:
        self.records.append(FillRecord("screenshot", (path,)))
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write a tiny PNG (1x1 transparent) so file is real and inspectable
        path.write_bytes(_TINY_PNG)
        self.screenshot_path = path
        return path

    async def close(self) -> None:
        self.records.append(FillRecord("close"))
        self.closed = True

    def call_sequence(self) -> list[str]:
        """Return ['goto', 'fill', 'fill', ..., 'submit', 'screenshot', 'close'] for assertions."""
        return [r.method for r in self.records]


# Smallest valid PNG (1x1 transparent). Used for screenshot placeholders.
_TINY_PNG = bytes.fromhex(
    "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C489"
    "0000000A49444154789C63000100000005000179A363010000000049454E44AE426082"
)


def make_fake(**kwargs: Any) -> FakePlaywrightClient:
    """Helper: build a fake with given kwargs (sugar for tests)."""
    return FakePlaywrightClient(**kwargs)
