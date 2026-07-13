from __future__ import annotations

from io import BytesIO
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter

SHEET_COLUMNS = {
    "Users": ["code", "name", "role", "active", "sort_order"],
    "Objects": ["code", "name", "execution_method", "default_contractor_code", "active", "sort_order"],
    "Stages": ["code", "name", "active", "sort_order"],
    "ObjectStages": ["object_code", "stage_code", "active"],
    "Contractors": ["code", "name", "active", "sort_order"],
    "Units": ["code", "name", "symbol", "active", "sort_order"],
    "Equipment": ["code", "name", "default_unit_code", "active", "sort_order"],
    "WorkTypes": ["code", "name", "default_unit_code", "active", "sort_order"],
    "WorkMethods": ["code", "name", "active", "sort_order"],
    "WorkTypeMethods": ["work_type_code", "work_method_code", "active"],
    "Assignments": ["user_code", "object_code", "active_from", "active_to", "schedule_type", "active"],
}

SHEET_ORDER = [
    "Users",
    "Contractors",
    "Units",
    "Objects",
    "Stages",
    "ObjectStages",
    "Equipment",
    "WorkTypes",
    "WorkMethods",
    "WorkTypeMethods",
    "Assignments",
]


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text


def _normalize_bool(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip().lower()
    if text in ("1", "true", "yes", "да"):
        return True
    if text in ("0", "false", "no", "нет"):
        return False
    return bool(text)


def build_template() -> BytesIO:
    """Build an empty catalog import template workbook."""
    wb = Workbook()
    # Remove default sheet; recreate in order.
    wb.remove(wb.active)
    for sheet_name in SHEET_ORDER:
        ws = wb.create_sheet(title=sheet_name)
        columns = SHEET_COLUMNS[sheet_name]
        ws.append(columns)
        for col_idx, _col in enumerate(columns, start=1):
            ws.column_dimensions[get_column_letter(col_idx)].width = 20
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def _read_sheet_rows(ws) -> list[dict]:
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [_normalize_text(cell).lower() for cell in rows[0]]
    result = []
    for row in rows[1:]:
        record = {}
        for idx, header in enumerate(headers):
            record[header] = row[idx] if idx < len(row) else None
        result.append(record)
    return result


class CatalogImportValidator:
    """Validate an uploaded catalog Excel workbook and produce a preview."""

    def __init__(self, workbook_bytes: bytes) -> None:
        self._wb = load_workbook(filename=BytesIO(workbook_bytes), data_only=True)
        self._errors: list[dict] = []
        self._preview: dict = {}

    def validate(self) -> dict:
        for sheet_name in SHEET_ORDER:
            ws = self._wb[sheet_name] if sheet_name in self._wb.sheetnames else None
            if ws is None:
                continue
            rows = _read_sheet_rows(ws)
            self._preview[sheet_name] = {"create": 0, "update": 0, "deactivate": 0}
            self._validate_sheet(sheet_name, rows)
        return {"valid": not self._errors, "errors": self._errors, "preview": self._preview}

    def _add_error(self, sheet: str, row: int, message: str) -> None:
        self._errors.append({"sheet": sheet, "row": row, "message": message})

    def _validate_sheet(self, sheet_name: str, rows: list[dict]) -> None:
        columns = SHEET_COLUMNS[sheet_name]
        required = {"code"} if "code" in columns else set()
        codes_seen: dict[str, int] = {}

        for idx, row in enumerate(rows, start=2):
            for col in required:
                value = _normalize_text(row.get(col))
                if not value:
                    self._add_error(sheet_name, idx, f"Пустое обязательное поле '{col}'")
                    continue

            code = _normalize_text(row.get("code"))
            if code:
                if code in codes_seen:
                    self._add_error(
                        sheet_name,
                        idx,
                        f"Дублирующийся code '{code}' (строка {codes_seen[code]})",
                    )
                else:
                    codes_seen[code] = idx

            if sheet_name == "Objects":
                method = _normalize_text(row.get("execution_method"))
                if method and method not in ("own", "contractor"):
                    self._add_error(
                        sheet_name, idx, f"execution_method '{method}' не из own|contractor"
                    )

            if sheet_name == "ObjectStages":
                obj_code = _normalize_text(row.get("object_code"))
                stage_code = _normalize_text(row.get("stage_code"))
                if not obj_code:
                    self._add_error(sheet_name, idx, "Пустое обязательное поле 'object_code'")
                if not stage_code:
                    self._add_error(sheet_name, idx, "Пустое обязательное поле 'stage_code'")

            if sheet_name == "Users":
                role = _normalize_text(row.get("role"))
                if role and role not in ("responsible", "manager", "admin"):
                    self._add_error(sheet_name, idx, f"role '{role}' не из responsible|manager|admin")

            active = _normalize_bool(row.get("active"))
            if active:
                self._preview[sheet_name]["create" if code else "update"] += 1
            else:
                self._preview[sheet_name]["deactivate"] += 1
