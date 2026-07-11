"""Golden test: for each fixture, the fill_form call sequence must match a saved snapshot.

To regenerate:  .venv/bin/python scripts/_gen_golden_fill_sequences.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.forms import FakePlaywrightClient
from backend.forms.filler import fill_form
from backend.schemas import Report

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "golden"
REPORTS_DIR = Path(__file__).parent / "fixtures" / "reports"


def _golden_report(name: str) -> Report:
    p = GOLDEN_DIR / f"{name}.json"
    return Report.model_validate_json(p.read_text(encoding="utf-8"))


def _golden_sequence(name: str) -> list[dict]:
    p = GOLDEN_DIR / f"{name}.fill_sequence.json"
    if not p.exists():
        pytest.skip(f"no golden sequence for {name}")
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "name",
    ["foreman_stepanov_2026-07-10", "foreman_kaznadeev_2026-07-10", "foreman_trofimov_2026-07-10"],
)
@pytest.mark.asyncio
async def test_fill_sequence_matches_golden(name: str, tmp_path: Path) -> None:
    """Capture the fill sequence; assert it matches the saved golden snapshot."""
    report = _golden_report(name)
    fake = FakePlaywrightClient()
    await fill_form(report, "https://forms.yandex.ru/x", fake, screenshot_dir=tmp_path, screenshot_name=f"{name}.png")

    actual = []
    for r in fake.records:
        entry: dict = {"method": r.method}
        if r.method == "fill":
            entry["selector"] = r.args[0]
            entry["value"] = r.args[1]
        elif r.method == "goto":
            entry["url"] = r.args[0]
        actual.append(entry)

    expected = _golden_sequence(name)
    assert actual == expected, f"fill sequence drift for {name}"
