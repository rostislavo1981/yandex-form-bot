"""Build Excel summary workbook from a list of Reports.

Form is about machines + personnel, not just works. New columns:
Дата | Объект | Прораб | Техника (список) | Люди (ИТР/ОПР-ш/ОПР-в) | Грунт м³ | Комментарии | Подтверждено
"""
from __future__ import annotations

import logging
from collections.abc import Iterable
from pathlib import Path

from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from backend.excel import (
    BORDER,
    CONFIRMED_FILL,
    HEADER_FILL,
    HEADER_FONT,
    safe_str,
)
from backend.schemas import Report

logger = logging.getLogger(__name__)


HEADERS = [
    "Дата",
    "Объект",
    "Прораб",
    "Техника",
    "Ед.",
    "Кол-во",
    "ИТР",
    "ОПР (штат)",
    "ОПР (внешт.)",
    "Всего людей",
    "Грунт, м³",
    "Погода",
    "Комментарий прораба",
    "Итоговый комментарий",
    "Подтверждено",
]


def _format_quantity(v: float, unit: str) -> str:
    if v == 0:
        return ""
    if isinstance(v, float) and v.is_integer():
        return f"{int(v)} {unit}".strip()
    return f"{v:g} {unit}".strip()


def _row_from_report(report: Report, *, confirmed: bool) -> list[object]:
    machines_strs = [m.machine_type for m in report.machines if m.machine_type]
    machines_qty = [
        _format_quantity(m.quantity, m.unit) for m in report.machines if m.machine_type
    ]
    # First row shows first machine; rest goes into comment (or we just show all)
    main_machine = "; ".join(machines_strs) if machines_strs else ""
    main_qty = "; ".join(machines_qty) if machines_qty else ""
    main_unit = (
        "; ".join(m.unit for m in report.machines if m.machine_type)
        if machines_strs else ""
    )
    p = report.personnel
    return [
        report.date.isoformat(),
        report.object_name,
        report.foreman,
        main_machine,
        main_unit,
        main_qty,
        p.itr,
        p.opr_staff,
        p.opr_external,
        p.total,
        report.waste_volume,
        safe_str(report.weather),
        safe_str(report.comment),
        safe_str(report.final_comment),
        "✅" if confirmed else "⏳",
    ]


def build_summary(
    reports: Iterable[tuple[Report, bool]],
    output_path: Path,
) -> Path:
    """Write a fresh workbook to output_path. Returns the path."""
    wb = Workbook()
    ws: Worksheet = wb.active
    assert ws is not None
    ws.title = "Сводная"

    # Header row
    for col_idx, header in enumerate(HEADERS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.border = BORDER

    row_idx = 2
    for report, confirmed in reports:
        row = _row_from_report(report, confirmed=confirmed)
        for col_idx, value in enumerate(row, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = BORDER
            if confirmed:
                cell.fill = CONFIRMED_FILL
        row_idx += 1

    # Auto-width
    for col_idx, header in enumerate(HEADERS, start=1):
        max_len = len(str(header))
        for r in range(2, min(row_idx, 12)):
            v = ws.cell(row=r, column=col_idx).value
            if v is not None:
                max_len = max(max_len, min(50, len(str(v))))
        ws.column_dimensions[get_column_letter(col_idx)].width = max_len + 2

    ws.freeze_panes = "A2"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(output_path))
    logger.info("build_summary: wrote %d rows to %s", row_idx - 2, output_path)
    return output_path
