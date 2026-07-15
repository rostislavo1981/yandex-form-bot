"""Tests for backend.excel — REAL form (machines + personnel)."""
from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import load_workbook

from backend.excel import safe_float, safe_str
from backend.excel.summary import build_summary
from backend.schemas import MachineItem, Personnel, Report


def test_safe_str_none_is_empty() -> None:
    assert safe_str(None) == ""


def test_safe_str_nan_is_empty() -> None:
    assert safe_str("nan") == ""
    assert safe_str("NaN") == ""
    assert safe_str("None") == ""


def test_safe_str_normal_values() -> None:
    assert safe_str("hello") == "hello"
    assert safe_str(42) == "42"
    assert safe_str(3.14) == "3.14"


def test_safe_float_handles_edge_cases() -> None:
    assert safe_float(None) == 0.0
    assert safe_float("") == 0.0
    assert safe_float("not a number") == 0.0
    assert safe_float("3.14") == pytest.approx(3.14)
    assert safe_float(42) == 42.0


def _make_report(
    foreman: str = "Степанов", object_name: str = "РП-7 Каменка"
) -> Report:
    return Report(
        date="2026-07-10",
        object_name=object_name,
        foreman=foreman,
        machines=[
            MachineItem(machine_type="Экскаватор JCB 3CX", unit="час", quantity=8),
            MachineItem(machine_type="Кран автомобильный", unit="смена", quantity=1),
        ],
        waste_volume=15.0,
        personnel=Personnel(itr=1, opr_staff=4, opr_external=0),
        comment="норм",
        weather="ясно",
    )


def test_build_summary_creates_file(tmp_path: Path) -> None:
    out = build_summary([(_make_report(), True)], tmp_path / "summary.xlsx")
    assert out.exists()
    assert out.stat().st_size > 1000


def test_build_summary_two_reports(tmp_path: Path) -> None:
    r1 = _make_report(foreman="Степанов", object_name="РП-7")
    r2 = _make_report(foreman="Казнадеев", object_name="ТП-345")
    out = build_summary([(r1, True), (r2, False)], tmp_path / "summary.xlsx")
    wb = load_workbook(out)
    ws = wb.active
    # 1 header + 2 data = 3 rows
    assert ws.max_row == 3
    assert ws.cell(row=1, column=1).value == "Тип"
    assert ws.cell(row=2, column=1).value == "Прораб"
    assert ws.cell(row=2, column=2).value == "2026-07-10"
    assert ws.cell(row=2, column=3).value == "РП-7"
    assert ws.cell(row=2, column=4).value == "Степанов"
    assert ws.cell(row=2, column=8).value == 1  # itr
    assert ws.cell(row=2, column=9).value == 4  # opr_staff
    assert ws.cell(row=2, column=11).value == 5  # total
    assert ws.cell(row=2, column=12).value == 15  # waste
    assert ws.cell(row=3, column=3).value == "ТП-345"
    assert ws.cell(row=3, column=16).value == "⏳"  # not confirmed


def test_build_summary_personnel_total(tmp_path: Path) -> None:
    r = Report(
        date="2026-07-10",
        foreman="X",
        object_name="Y",
        personnel=Personnel(itr=2, opr_staff=3, opr_external=5),
    )
    out = build_summary([(r, True)], tmp_path / "summary.xlsx")
    wb = load_workbook(out)
    ws = wb.active
    assert ws.cell(row=2, column=11).value == 10  # total (shifted +1 for "Тип" col)


def test_build_summary_volume_rendered_without_dot_zero(tmp_path: Path) -> None:
    r = _make_report()
    out = build_summary([(r, True)], tmp_path / "summary.xlsx")
    wb = load_workbook(out)
    ws = wb.active
    # Waste volume col 12 should be 15 (integer, since Report stores it as float)
    assert ws.cell(row=2, column=12).value == 15


def test_build_summary_header_styled(tmp_path: Path) -> None:
    out = build_summary([(_make_report(), True)], tmp_path / "summary.xlsx")
    wb = load_workbook(out)
    ws = wb.active
    assert ws.cell(row=1, column=2).value == "Дата"  # shifted right by "Тип"
    assert ws.cell(row=1, column=1).font.bold is True


def test_build_summary_contractor_has_no_personnel(tmp_path: Path) -> None:
    """Contractor reports: type=contractor, personnel=None, columns show «—»."""
    r = _make_report(foreman="Иванов (подряд)", object_name="Синергия")
    r_obj = r[0] if isinstance(r, tuple) else r
    r_obj.type = "contractor"
    r_obj.personnel = None
    out = build_summary([(r_obj, True)], tmp_path / "summary.xlsx")
    wb = load_workbook(out)
    ws = wb.active
    assert ws.cell(row=2, column=1).value == "Подрядчик"
    assert ws.cell(row=2, column=8).value == "—"  # itr
    assert ws.cell(row=2, column=9).value == "—"  # opr_staff
    assert ws.cell(row=2, column=10).value == "—"  # opr_external
    assert ws.cell(row=2, column=11).value == "—"  # total
    assert ws.cell(row=2, column=12).value == 15  # waste still rendered


def test_build_summary_empty_input(tmp_path: Path) -> None:
    out = build_summary([], tmp_path / "summary.xlsx")
    wb = load_workbook(out)
    ws = wb.active
    assert ws.max_row == 1


def test_build_summary_yellow_for_confirmed(tmp_path: Path) -> None:
    r = _make_report()
    out = build_summary([(r, True)], tmp_path / "summary.xlsx")
    wb = load_workbook(out)
    ws = wb.active
    cell = ws.cell(row=2, column=1)
    rgb = cell.fill.start_color.rgb
    assert rgb in ("FFFFF2CC", "00FFF2CC")
