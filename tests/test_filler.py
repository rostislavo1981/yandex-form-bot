"""Tests for backend.forms.filler.fill_form — REAL form (12 fields)."""
from __future__ import annotations

from pathlib import Path

import pytest

from backend.forms import FakePlaywrightClient, FormFillError
from backend.forms.fields import get_field
from backend.forms.filler import fill_form, value_to_str
from backend.schemas import Report


@pytest.fixture
def stepanov_report() -> Report:
    return Report(
        date="2026-07-10",
        foreman="Степанов",
        object_name="РП-7 Каменка",
        machines=[
            {"machine_type": "Экскаватор JCB 3CX", "unit": "час", "quantity": 8},
            {"machine_type": "Кран автомобильный", "unit": "смена", "quantity": 1},
        ],
        waste_volume=15.0,
        personnel={"itr": 1, "opr_staff": 4, "opr_external": 0},
    )


@pytest.mark.asyncio
async def test_fill_form_happy_path(stepanov_report: Report, tmp_path: Path) -> None:
    fake = FakePlaywrightClient()
    out = await fill_form(
        stepanov_report,
        "https://forms.yandex.ru/x",
        fake,
        screenshot_dir=tmp_path,
        screenshot_name="stepanov.png",
    )
    assert out == tmp_path / "stepanov.png"
    assert out.exists()
    seq = fake.call_sequence()
    assert seq[0] == "goto"
    assert seq[-1] == "screenshot"
    assert "submit" in seq
    # 12 fields in payload, but comment/final_comment empty + machine_quantity=0 may skip
    # Степанов fixture has final_comment=None + comment=None → both skipped (empty string)
    # Real filled count: 12 - skipped empties
    assert 10 <= len(fake.filled) <= 12, f"expected 10-12 fills, got {len(fake.filled)}"


@pytest.mark.asyncio
async def test_fill_form_no_machines(tmp_path: Path) -> None:
    """Empty machines: machine_type is empty -> skipped."""
    r = Report(date="2026-07-10", foreman="X", object_name="Y")
    fake = FakePlaywrightClient()
    await fill_form(r, "https://x", fake, screenshot_dir=tmp_path, screenshot_name="x.png")
    # machine_type="" skipped, machine_unit default "час" -> filled, quantity=0 -> filled
    assert get_field("machine_type").selector not in fake.filled


@pytest.mark.asyncio
async def test_fill_form_selector_missing_raises(tmp_path: Path) -> None:
    r = Report(date="2026-07-10", foreman="X", object_name="Y")
    fake = FakePlaywrightClient(selectors_not_found={get_field("date").selector})
    with pytest.raises(FormFillError, match="selector not found"):
        await fill_form(r, "https://x", fake, screenshot_dir=tmp_path, screenshot_name="x.png")


@pytest.mark.asyncio
async def test_fill_form_submit_failure_raises(tmp_path: Path) -> None:
    r = Report(date="2026-07-10", foreman="X", object_name="Y")
    fake = FakePlaywrightClient(submit_should_succeed=False)
    with pytest.raises(FormFillError, match="submit failed"):
        await fill_form(r, "https://x", fake, screenshot_dir=tmp_path, screenshot_name="x.png")


@pytest.mark.asyncio
async def test_fill_form_two_machines_extras_in_comment(tmp_path: Path) -> None:
    """Excess machines packed into comment."""
    r = Report(
        date="2026-07-10",
        foreman="X",
        object_name="Y",
        machines=[
            {"machine_type": "A", "unit": "час", "quantity": 4},
            {"machine_type": "B", "unit": "смена", "quantity": 1},
        ],
    )
    fake = FakePlaywrightClient()
    await fill_form(r, "https://x", fake, screenshot_dir=tmp_path, screenshot_name="x.png")
    comment_value = fake.filled[get_field("comment").selector]
    assert "доп. техника" in comment_value
    assert "B 1 смена" in comment_value


# === value_to_str (regression for the openpyxl-style None bug) ============

def test_value_to_str_none_returns_empty() -> None:
    assert value_to_str(None) == ""


def test_value_to_str_float_renders_as_int_when_whole() -> None:
    assert value_to_str(50.0) == "50"
    assert value_to_str(3.5) == "3.5"


def test_value_to_str_int_passes() -> None:
    assert value_to_str(42) == "42"


def test_value_to_str_string_passes() -> None:
    assert value_to_str("hello") == "hello"


def test_value_to_str_empty_string_passes() -> None:
    assert value_to_str("") == ""
