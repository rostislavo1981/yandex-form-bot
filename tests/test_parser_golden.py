"""Golden test: for each fixture, fake LLM returns the golden JSON, parser must produce equal Report."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.llm.parser import parse_report

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "golden"
REPORTS_DIR = Path(__file__).parent / "fixtures" / "reports"


class GoldenFakeLLM:
    def __init__(self, golden: dict) -> None:
        self.golden = golden
        self.calls = 0

    async def complete(self, user_text: str, system_text: str | None = None) -> str:
        self.calls += 1
        return json.dumps(self.golden, ensure_ascii=False)


def _golden_for(report_file: Path) -> dict:
    name = report_file.stem
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

    actual = report.model_dump(mode="json")
    assert actual["date"] == golden["date"]
    assert actual["foreman"] == golden["foreman"]
    assert actual["object_name"] == golden["object_name"]
    assert len(actual["machines"]) == len(golden["machines"])
    for am, gm in zip(actual["machines"], golden["machines"], strict=True):
        assert am["machine_type"] == gm["machine_type"]
        assert float(am["quantity"]) == float(gm["quantity"])
        assert am["unit"] == gm["unit"]
    assert float(actual["waste_volume"]) == float(golden["waste_volume"])
    assert actual["personnel"]["itr"] == golden["personnel"]["itr"]
    assert actual["personnel"]["opr_staff"] == golden["personnel"]["opr_staff"]
    assert actual["personnel"]["opr_external"] == golden["personnel"]["opr_external"]
    assert (actual.get("final_comment") or None) == (golden.get("final_comment") or None)
    assert (actual.get("comment") or None) == (golden.get("comment") or None)
    assert (actual.get("weather") or None) == (golden.get("weather") or None)
    assert fake.calls == 1, "golden JSON should be accepted on first try"
