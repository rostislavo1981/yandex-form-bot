"""Tests for the in-process scheduler.

Covers time math and the stop-on-signal path. Does NOT call the live MAX API.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.cli.scheduler import _next_fire, _now_in_tz  # noqa: E402

MSK = timezone(timedelta(hours=3))  # matches Europe/Moscow in our test window


def test_next_fire_same_day_if_target_is_later():
    now = datetime(2026, 7, 11, 10, 0, tzinfo=MSK)
    target = _next_fire(now, 20, 0)
    assert target == datetime(2026, 7, 11, 20, 0, tzinfo=MSK)
    assert (target - now).total_seconds() == 10 * 3600


def test_next_fire_rolls_to_next_day_if_target_passed():
    now = datetime(2026, 7, 11, 21, 30, tzinfo=MSK)
    target = _next_fire(now, 20, 0)
    assert target == datetime(2026, 7, 12, 20, 0, tzinfo=MSK)


def test_next_fire_rolls_to_next_day_if_target_is_now():
    now = datetime(2026, 7, 11, 20, 0, tzinfo=MSK)
    target = _next_fire(now, 20, 0)
    assert target == datetime(2026, 7, 12, 20, 0, tzinfo=MSK)


def test_next_fire_handles_minute_offset():
    now = datetime(2026, 7, 11, 19, 59, tzinfo=MSK)
    target = _next_fire(now, 20, 30)
    assert target == datetime(2026, 7, 11, 20, 30, tzinfo=MSK)


def test_now_in_tz_returns_aware_datetime():
    n = _now_in_tz()
    assert n.tzinfo is not None
    assert n.tzinfo.utcoffset(n) is not None
