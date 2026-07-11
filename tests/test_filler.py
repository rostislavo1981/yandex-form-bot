"""Tests for backend.forms.filler.fill_form."""
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
        object_name="РП-7 Каменка",
        foreman="Степанов",
        works=[
            {"name": "Копка траншеи", "volume": 50.0, "unit": "м", "people_count": 4},
            {"name": "Укладка кабеля", "volume": 50.0, "unit": "м"},
        ],
        materials=[{"name": "Кабель", "qty": 50.0, "unit": "м"}],
        notes="по плану",
        weather="ясно",
    )


@pytest.mark.asyncio
async def test_fill_form_happy_path(
    stepanov_report: Report, tmp_path: Path
) -> None:
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
    # Goto first, then fills, then submit, then screenshot
    seq = fake.call_sequence()
    assert seq[0] == "goto"
    assert seq[-1] == "screenshot"
    assert "submit" in seq
    # All non-empty fields were filled
    assert len(fake.filled) == 10  # MVP form has 10 fields, all populated


@pytest.mark.asyncio
async def test_fill_form_skips_empty_values(tmp_path: Path) -> None:
    """If report has only 1 work, work_2 fields with None value should not be touched."""
    r = Report(
        date="2026-07-10",
        object_name="X",
        foreman="Y",
        works=[{"name": "Копка", "volume": 10.0, "unit": "м"}],
    )
    fake = FakePlaywrightClient()
    await fill_form(r, "https://x", fake, screenshot_dir=tmp_path, screenshot_name="x.png")
    # work_2_name: "" skipped, work_2_volume: 0.0 -> "0" NOT skipped (numeric)
    # So we only assert that the empty-string fields are not in filled:
    assert get_field("work_2_name").selector not in fake.filled
    # work_1 was filled
    assert fake.filled[get_field("work_1_name").selector] == "Копка"


@pytest.mark.asyncio
async def test_fill_form_selector_missing_raises(tmp_path: Path) -> None:
    r = Report(
        date="2026-07-10",
        object_name="X",
        foreman="Y",
        works=[{"name": "Копка", "volume": 1.0, "unit": "м"}],
    )
    # Mark the date selector as missing
    fake = FakePlaywrightClient(selectors_not_found={get_field("date").selector})
    with pytest.raises(FormFillError, match="selector not found"):
        await fill_form(r, "https://x", fake, screenshot_dir=tmp_path, screenshot_name="x.png")


@pytest.mark.asyncio
async def test_fill_form_submit_failure_raises(tmp_path: Path) -> None:
    r = Report(
        date="2026-07-10",
        object_name="X",
        foreman="Y",
        works=[],
    )
    fake = FakePlaywrightClient(submit_should_succeed=False)
    with pytest.raises(FormFillError, match="submit failed"):
        await fill_form(r, "https://x", fake, screenshot_dir=tmp_path, screenshot_name="x.png")


@pytest.mark.asyncio
async def test_fill_form_three_works_extras_in_notes(tmp_path: Path) -> None:
    """More than 2 works: extras should be in notes, not as separate fields."""
    r = Report(
        date="2026-07-10",
        object_name="X",
        foreman="Y",
        works=[
            {"name": "A", "volume": 1.0, "unit": "м"},
            {"name": "B", "volume": 1.0, "unit": "м"},
            {"name": "C", "volume": 1.0, "unit": "м"},
        ],
    )
    fake = FakePlaywrightClient()
    await fill_form(r, "https://x", fake, screenshot_dir=tmp_path, screenshot_name="x.png")
    notes_value = fake.filled[get_field("notes").selector]
    assert "доп. работы" in notes_value
    assert "C 1 м" in notes_value


# === value_to_str (regression for the openpyxl-style None bug) ============

def test_value_to_str_none_returns_empty() -> None:
    """The 'str(None).strip() == None' trap. Must return empty string, not 'None'."""
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
