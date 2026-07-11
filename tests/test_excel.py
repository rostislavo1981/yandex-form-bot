"""Tests for backend.excel (styles + build_summary)."""
from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import load_workbook

from backend.excel import safe_float, safe_str
from backend.excel.summary import build_summary
from backend.schemas import Report


def test_safe_str_none_is_empty() -> None:
    assert safe_str(None) == ""


def test_safe_str_nan_is_empty() -> None:
    assert safe_str("nan") == ""
    assert safe_str("NaN") == ""
    assert safe_str("None") == ""  # the openpyxl str(None) trap


def test_safe_str_normal_values() -> None:
    assert safe_str("hello") == "hello"
    assert safe_str(42) == "42"
    assert safe_str(3.14) == "3.14"
    assert safe_str("") == ""


def test_safe_float_handles_edge_cases() -> None:
    assert safe_float(None) == 0.0
    assert safe_float("") == 0.0
    assert safe_float("not a number") == 0.0
    assert safe_float("3.14") == pytest.approx(3.14)
    assert safe_float(42) == 42.0
    assert safe_float(0) == 0.0


def _make_report(
    foreman: str = "Степанов", object_name: str = "РП-7", with_two_works: bool = True
) -> Report:
    works: list[dict] = [
        {"name": "Копка", "volume": 50.0, "unit": "м", "people_count": 4},
    ]
    if with_two_works:
        works.append({"name": "Укладка", "volume": 50.0, "unit": "м"})
    return Report(
        date="2026-07-10",
        object_name=object_name,
        foreman=foreman,
        works=works,
        materials=[{"name": "Кабель", "qty": 50.0, "unit": "м"}],
        notes="по плану",
        weather="ясно",
    )


def test_build_summary_creates_file(tmp_path: Path) -> None:
    r1 = _make_report()
    out = build_summary([(r1, True)], tmp_path / "summary.xlsx")
    assert out.exists()
    assert out.stat().st_size > 1000  # real xlsx, not empty


def test_build_summary_two_reports(tmp_path: Path) -> None:
    r1 = _make_report(foreman="Степанов", object_name="РП-7")
    r2 = _make_report(foreman="Казнадеев", object_name="ТП-345")
    out = build_summary([(r1, True), (r2, False)], tmp_path / "summary.xlsx")
    wb = load_workbook(out)
    ws = wb.active
    # 1 header + 2 data = 3 rows
    assert ws.max_row == 3
    assert ws.cell(row=2, column=1).value == "2026-07-10"
    assert ws.cell(row=2, column=2).value == "РП-7"
    assert ws.cell(row=2, column=3).value == "Степанов"
    assert ws.cell(row=3, column=2).value == "ТП-345"
    assert ws.cell(row=3, column=13).value == "⏳"  # not confirmed


def test_build_summary_volume_rendered_without_dot_zero(tmp_path: Path) -> None:
    r = _make_report()
    out = build_summary([(r, True)], tmp_path / "summary.xlsx")
    wb = load_workbook(out)
    ws = wb.active
    # Work 1 volume column (5) should be "50 м", not "50.0 м"
    assert ws.cell(row=2, column=5).value == "50 м"


def test_build_summary_uses_yellow_for_confirmed(tmp_path: Path) -> None:

    r = _make_report()
    out = build_summary([(r, True)], tmp_path / "summary.xlsx")
    wb = load_workbook(out)
    ws = wb.active
    cell = ws.cell(row=2, column=1)
    assert cell.fill.start_color.rgb in ("FFFFF2CC", "00FFF2CC")


def test_build_summary_header_styled(tmp_path: Path) -> None:
    out = build_summary([(_make_report(), True)], tmp_path / "summary.xlsx")
    wb = load_workbook(out)
    ws = wb.active
    assert ws.cell(row=1, column=1).value == "Дата"
    # bold header
    assert ws.cell(row=1, column=1).font.bold is True


def test_build_summary_empty_input(tmp_path: Path) -> None:
    """Empty list -> just the header row."""
    out = build_summary([], tmp_path / "summary.xlsx")
    wb = load_workbook(out)
    ws = wb.active
    assert ws.max_row == 1
    assert ws.cell(row=1, column=1).value == "Дата"


def test_build_summary_three_works_extras_in_column(tmp_path: Path) -> None:
    r = Report(
        date="2026-07-10",
        object_name="X",
        foreman="Y",
        works=[
            {"name": "A", "volume": 10.0, "unit": "м"},
            {"name": "B", "volume": 10.0, "unit": "м"},
            {"name": "C", "volume": 10.0, "unit": "м"},
        ],
    )
    out = build_summary([(r, True)], tmp_path / "summary.xlsx")
    wb = load_workbook(out)
    ws = wb.active
    # Col 10 = "Доп. работы"
    extras = ws.cell(row=2, column=10).value
    assert "10 м" in extras
