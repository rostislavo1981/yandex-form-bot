"""Tests for backend.forms (FakePlaywrightClient)."""
from __future__ import annotations

from pathlib import Path

import pytest

from backend.forms import (
    FakePlaywrightClient,
    FormFillError,
    PlaywrightFormClient,
    make_fake,
)


@pytest.mark.asyncio
async def test_fake_records_goto() -> None:
    f = FakePlaywrightClient()
    await f.goto("https://forms.yandex.ru/x")
    assert f.goto_url == "https://forms.yandex.ru/x"
    assert f.call_sequence() == ["goto"]


@pytest.mark.asyncio
async def test_fake_records_fill_in_order() -> None:
    f = FakePlaywrightClient()
    await f.fill('input[name="a"]', "1")
    await f.fill('input[name="b"]', "2")
    assert f.filled == {'input[name="a"]': "1", 'input[name="b"]': "2"}


@pytest.mark.asyncio
async def test_fake_selector_not_found_raises() -> None:
    f = FakePlaywrightClient(selectors_not_found={'input[name="x"]'})
    with pytest.raises(FormFillError, match="selector not found"):
        await f.fill('input[name="x"]', "1")


@pytest.mark.asyncio
async def test_fake_submit_failure_raises() -> None:
    f = FakePlaywrightClient(submit_should_succeed=False)
    await f.goto("u")
    await f.fill('input[name="a"]', "1")
    with pytest.raises(FormFillError, match="submit failed"):
        await f.submit()
    assert not f.submitted


@pytest.mark.asyncio
async def test_fake_screenshot_writes_file(tmp_path: Path) -> None:
    f = FakePlaywrightClient()
    p = tmp_path / "sub" / "x.png"
    out = await f.screenshot(p)
    assert out == p
    assert p.exists()
    # PNG magic bytes
    assert p.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.mark.asyncio
async def test_fake_satisfies_protocol() -> None:
    """FakePlaywrightClient must satisfy the runtime-checkable Protocol."""
    f = FakePlaywrightClient()
    assert isinstance(f, PlaywrightFormClient)


def test_make_fake_helper() -> None:
    f = make_fake(submit_should_succeed=False)
    assert isinstance(f, FakePlaywrightClient)
    assert f._submit_should_succeed is False
