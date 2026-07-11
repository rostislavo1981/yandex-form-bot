"""Golden test: for each fixture, fake LLM returns the golden JSON, parser must produce equal Report.

This is the closest we can get to end-to-end testing without hitting a real LLM.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.llm.parser import parse_report

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "golden"
REPORTS_DIR = Path(__file__).parent / "fixtures" / "reports"


class GoldenFakeLLM:
    """Returns the golden JSON (from a .json file) for the matching fixture."""

    def __init__(self, golden: dict) -> None:
        self.golden = golden
        self.calls = 0

    async def complete(self, user_text: str, system_text: str | None = None) -> str:
        self.calls += 1
        return json.dumps(self.golden, ensure_ascii=False)


def _golden_for(report_file: Path) -> dict:
    name = report_file.stem  # e.g. foreman_stepanov_2026-07-10
    golden_path = GOLDEN_DIR / f"{name}.json"
    assert golden_path.exists(), f"missing golden for {report_file.name}"
    return json.loads(golden_path.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "report_file",
    [
        REPORTS_DIR / "foreman_stepanov_2026-07-10.txt",
        REPORTS_DIR / "foreman_kaznadeev_2026-07-10.txt",
        REPORTS_DIR / "foreman_trofimov_2026-07-10.txt",
    ],
)
@pytest.mark.asyncio
async def test_parser_produces_golden_report(report_file: Path) -> None:
    golden = _golden_for(report_file)
    text = report_file.read_text(encoding="utf-8")
    fake = GoldenFakeLLM(golden)
    report = await parse_report(text, fake)

    # Round-trip to dict for stable comparison (Pydantic normalizes)
    actual = report.model_dump(mode="json")
    # Drop notes if both are null-equivalent to avoid float-y issues
    assert actual["date"] == golden["date"]
    assert actual["object_name"] == golden["object_name"]
    assert actual["foreman"] == golden["foreman"]
    assert len(actual["works"]) == len(golden["works"])
    for aw, gw in zip(actual["works"], golden["works"], strict=True):
        assert aw["name"] == gw["name"]
        assert float(aw["volume"]) == float(gw["volume"])
        assert aw["unit"] == gw["unit"]
        assert aw["people_count"] == gw["people_count"]
    assert len(actual["materials"]) == len(golden["materials"])
    for am, gm in zip(actual["materials"], golden["materials"], strict=True):
        assert am["name"] == gm["name"]
        assert float(am["qty"]) == float(gm["qty"])
        assert am["unit"] == gm["unit"]
    # notes / weather can be null vs "" — normalize
    assert (actual.get("notes") or None) == (golden.get("notes") or None)
    assert (actual.get("weather") or None) == (golden.get("weather") or None)
    assert fake.calls == 1, "golden JSON should be accepted on first try"
