"""Tests for backend.llm.parser (REAL form schema)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.llm.parser import ParseError, parse_report

VALID_REPORT_JSON = json.dumps(
    {
        "date": "2026-07-10",
        "foreman": "Степанов",
        "object_name": "РП-7 Каменка",
        "comment": None,
        "machines": [
            {"machine_type": "Экскаватор JCB", "unit": "час", "quantity": 8}
        ],
        "waste_volume": 15,
        "personnel": {"itr": 1, "opr_staff": 4, "opr_external": 0},
        "final_comment": None,
        "weather": "ясно",
    },
    ensure_ascii=False,
)


class FakeLLM:
    def __init__(self, *responses: str) -> None:
        self.responses = list(responses)
        self.call_count = 0

    async def complete(self, user_text: str, system_text: str | None = None) -> str:
        self.call_count += 1
        if not self.responses:
            raise RuntimeError("FakeLLM: no more responses")
        return self.responses.pop(0)


@pytest.mark.asyncio
async def test_happy_path() -> None:
    fake = FakeLLM(VALID_REPORT_JSON)
    r = await parse_report("любой текст", fake)
    assert r.foreman == "Степанов"
    assert r.machines[0].quantity == 8
    assert r.personnel.itr == 1
    assert r.waste_volume == 15
    assert fake.call_count == 1


@pytest.mark.asyncio
async def test_broken_json_then_fix_succeeds() -> None:
    fake = FakeLLM("not json at all", VALID_REPORT_JSON)
    r = await parse_report("текст", fake)
    assert r.object_name == "РП-7 Каменка"
    assert fake.call_count == 2


@pytest.mark.asyncio
async def test_both_attempts_fail_raises_parse_error() -> None:
    fake = FakeLLM("not json", "still not json")
    with pytest.raises(ParseError, match="Could not parse report"):
        await parse_report("текст", fake)
    assert fake.call_count == 2


@pytest.mark.asyncio
async def test_empty_text_raises() -> None:
    fake = FakeLLM("ignored")
    with pytest.raises(ParseError, match="empty"):
        await parse_report("", fake)
    assert fake.call_count == 0


@pytest.mark.asyncio
async def test_markdown_fences_are_stripped() -> None:
    fenced = "```json\n" + VALID_REPORT_JSON + "\n```"
    fake = FakeLLM(fenced)
    r = await parse_report("текст", fake)
    assert r.object_name == "РП-7 Каменка"


@pytest.mark.asyncio
async def test_validation_error_missing_fields_then_fix() -> None:
    """If LLM returns JSON missing required fields, retry picks up VALID."""
    bad = json.dumps({"date": "2026-07-10"})  # missing foreman, object_name
    fake = FakeLLM(bad, VALID_REPORT_JSON)
    r = await parse_report("текст", fake)
    assert r.foreman == "Степанов"


@pytest.mark.asyncio
async def test_real_fixture_text_does_not_crash_parser() -> None:
    fixtures = Path(__file__).parent / "fixtures" / "reports"
    for f in fixtures.glob("*.txt"):
        text = f.read_text(encoding="utf-8")
        assert len(text) > 50
        assert " " in text
