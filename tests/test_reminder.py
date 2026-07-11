"""Tests for the daily reminder CLI.

These run offline — they stub MaxClient with a fake.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.cli.send_reminder import _load_subscribers, _send_all, main  # noqa: E402


class _FakeMax:
    def __init__(self, token: str, **kwargs):
        self.token = token
        self.sent: list[tuple[str, str]] = []

    async def close(self):
        pass

    async def send_message(self, chat_id, text):
        self.sent.append((str(chat_id), text))
        return {"ok": True}


@pytest.mark.asyncio
async def test_send_all_calls_each_chat(monkeypatch):
    monkeypatch.setenv("MAX_BOT_TOKEN", "test-token")
    fake = _FakeMax("test-token")
    with patch("backend.cli.send_reminder.MaxClient", return_value=fake):
        ok, fail = await _send_all("hi {form_url}", ["111", "222"], "test-token")
    assert ok == 2
    assert fail == 0
    assert [c for c, _ in fake.sent] == ["111", "222"]


def test_load_subscribers_merges_env_and_file(monkeypatch, tmp_path):
    monkeypatch.setenv("REMINDER_CHAT_IDS", "1,2")
    subs = tmp_path / "subs.json"
    subs.write_text(json.dumps({"3": "a", "4": "b"}), encoding="utf-8")
    monkeypatch.setenv("SUBSCRIBERS_FILE", str(subs))
    monkeypatch.setenv("MAX_BOT_TOKEN", "t")

    # Bypass settings cache
    from backend import config as cfg
    cfg.reset_settings_cache()
    settings = cfg.get_settings()

    ids = _load_subscribers(settings)
    assert ids == ["1", "2", "3", "4"]


def test_load_subscribers_dedup(monkeypatch, tmp_path):
    monkeypatch.setenv("REMINDER_CHAT_IDS", "5,5,6")
    subs = tmp_path / "subs.json"
    subs.write_text(json.dumps({"5": "x", "7": "y"}), encoding="utf-8")
    monkeypatch.setenv("SUBSCRIBERS_FILE", str(subs))
    monkeypatch.setenv("MAX_BOT_TOKEN", "t")
    from backend import config as cfg
    cfg.reset_settings_cache()
    settings = cfg.get_settings()
    assert _load_subscribers(settings) == ["5", "6", "7"]


def test_main_no_subscribers_returns_zero(monkeypatch):
    monkeypatch.delenv("REMINDER_CHAT_IDS", raising=False)
    monkeypatch.setenv("MAX_BOT_TOKEN", "t")
    monkeypatch.setenv("SUBSCRIBERS_FILE", "/nonexistent.json")
    monkeypatch.setenv("FORM_PUBLISHED_URL", "https://example.com")
    from backend import config as cfg
    cfg.reset_settings_cache()
    assert main() == 0


def test_main_no_token_returns_nonzero(monkeypatch):
    monkeypatch.setenv("MAX_BOT_TOKEN", "")
    from backend import config as cfg
    cfg.reset_settings_cache()
    assert main() == 2
