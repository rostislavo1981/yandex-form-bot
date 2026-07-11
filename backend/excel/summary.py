"""Build Excel summary workbook from a list of Reports.

Layout: one sheet "Сводная", one row per submission.
Columns: Дата | Объект | Прораб | Работа 1 (имя) | Работа 1 (объём, ед.)
        | Работа 2 (имя) | Работа 2 (объём, ед.) | Материалы | Заметки | Подтверждено
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
    "Работа 1 — название",
    "Работа 1 — объём, ед.",
    "Работа 1 — людей",
    "Работа 2 — название",
    "Работа 2 — объём, ед.",
    "Работа 2 — людей",
    "Доп. работы",
    "Материалы",
    "Заметки",
    "Подтверждено",
]


def _format_volume(volume: float, unit: str) -> str:
    """Render 50.0 as '50 м' (not '50.0 м')."""
    if volume == 0:
        return ""
    if isinstance(volume, float) and volume.is_integer():
        return f"{int(volume)} {unit}".strip()
    return f"{volume:g} {unit}".strip()


def _format_work_item(item: dict | None) -> tuple[str, str, str]:
    """Returns (name, vol+unit, people)."""
    if not item:
        return "", "", ""
    name = safe_str(item.get("name"))
    vol = safe_str(item.get("volume"))
    unit = safe_str(item.get("unit"))
    people = safe_str(item.get("people_count"))
    if vol:
        try:
            v = float(vol)
            vol = _format_volume(v, unit) if unit else f"{v:g}"
        except (TypeError, ValueError):
            pass
    return name, vol, people


def _format_extras(works: list) -> str:
    """Works beyond the first 2."""
    if len(works) <= 2:
        return ""
    return "; ".join(_format_volume(w.volume, w.unit) for w in works[2:] if w.name)


def _format_materials(materials: list) -> str:
    return "; ".join(
        f"{m.name} {_format_volume(m.qty, m.unit)}" for m in materials if m.name
    )


def _row_from_report(report: Report, *, confirmed: bool) -> list[object]:
    w1 = _format_work_item(report.works[0].model_dump() if len(report.works) >= 1 else None)
    w2 = _format_work_item(report.works[1].model_dump() if len(report.works) >= 2 else None)
    return [
        report.date.isoformat(),
        report.object_name,
        report.foreman,
        w1[0], w1[1], w1[2],
        w2[0], w2[1], w2[2],
        _format_extras(report.works),
        _format_materials(report.materials),
        safe_str(report.notes),
        "✅" if confirmed else "⏳",
    ]


def build_summary(
    reports: Iterable[tuple[Report, bool]],
    output_path: Path,
) -> Path:
    """Write a fresh workbook to output_path. Returns the path.

    `reports` is an iterable of (Report, confirmed: bool) tuples.
    Overwrites output_path if it exists.
    """
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

    # Data rows
    row_idx = 2
    for report, confirmed in reports:
        row = _row_from_report(report, confirmed=confirmed)
        for col_idx, value in enumerate(row, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = BORDER
            if confirmed:
                cell.fill = CONFIRMED_FILL
        row_idx += 1

    # Auto-width: rough estimate
    for col_idx, header in enumerate(HEADERS, start=1):
        max_len = len(str(header))
        # Sample a few rows for content width
        for r in range(2, min(row_idx, 12)):
            v = ws.cell(row=r, column=col_idx).value
            if v is not None:
                max_len = max(max_len, min(50, len(str(v))))
        ws.column_dimensions[get_column_letter(col_idx)].width = max_len + 2

    # Freeze top row
    ws.freeze_panes = "A2"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(output_path))
    logger.info("build_summary: wrote %d rows to %s", row_idx - 2, output_path)
    return output_path
