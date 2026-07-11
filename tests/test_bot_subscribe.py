"""Tests for /start and /stop subscription flow."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.max.bot import (  # noqa: E402
    _handle_start,
    _handle_stop,
    _load_subscribers_file,
    _subscribe,
)


class _FakeMax:
    def __init__(self):
        self.sent: list[str] = []

    async def send_message(self, chat_id, text):
        self.sent.append(text)
        return {"ok": True}


@pytest.mark.asyncio
async def test_start_subscribes_new(tmp_path):
    fake = _FakeMax()
    await _handle_start("111", "/start", max_client=fake, data_dir=tmp_path)
    assert "Подписка оформлена" in fake.sent[0]
    assert _load_subscribers_file(tmp_path) == {"111": "111"}


@pytest.mark.asyncio
async def test_start_idempotent(tmp_path):
    _subscribe(tmp_path, "222", "stepanov")
    fake = _FakeMax()
    await _handle_start("222", "/start", max_client=fake, data_dir=tmp_path)
    assert "уже подписан" in fake.sent[0]
    assert _load_subscribers_file(tmp_path) == {"222": "stepanov"}


@pytest.mark.asyncio
async def test_stop_unsubscribes(tmp_path):
    _subscribe(tmp_path, "333", "ivan")
    fake = _FakeMax()
    await _handle_stop("333", "/stop", max_client=fake, data_dir=tmp_path)
    assert "отменена" in fake.sent[0]
    assert "333" not in _load_subscribers_file(tmp_path)


@pytest.mark.asyncio
async def test_stop_idempotent(tmp_path):
    fake = _FakeMax()
    await _handle_stop("999", "/stop", max_client=fake, data_dir=tmp_path)
    assert "не был подписан" in fake.sent[0]
