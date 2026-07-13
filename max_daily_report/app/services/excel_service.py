from __future__ import annotations

from io import BytesIO
from typing import Any

import sqlalchemy as sa
from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalogs import (
    Contractor,
    EquipmentType,
    Object,
    ObjectStage,
    Stage,
    Unit,
    WorkMethod,
    WorkType,
    WorkTypeMethod,
)
from app.models.operations import CatalogImport
from app.repos.catalogs import CatalogRepo

SHEET_COLUMNS = {
    "Users": ["code", "name", "role", "active", "sort_order"],
    "Objects": [
        "code",
        "name",
        "execution_method",
        "default_contractor_code",
        "active",
        "sort_order",
    ],
    "Stages": ["code", "name", "active", "sort_order"],
    "ObjectStages": ["object_code", "stage_code", "active"],
    "Contractors": ["code", "name", "active", "sort_order"],
    "Units": ["code", "name", "symbol", "active", "sort_order"],
    "Equipment": ["code", "name", "default_unit_code", "active", "sort_order"],
    "WorkTypes": ["code", "name", "default_unit_code", "active", "sort_order"],
    "WorkMethods": ["code", "name", "active", "sort_order"],
    "WorkTypeMethods": ["work_type_code", "work_method_code", "active"],
    "Assignments": [
        "user_code",
        "object_code",
        "active_from",
        "active_to",
        "schedule_type",
        "active",
    ],
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
    return str(value).strip()


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

    @property
    def preview(self) -> dict:
        return self._preview

    @property
    def errors(self) -> list[dict]:
        return self._errors

    def iter_rows(self, sheet_name: str) -> list[dict]:
        ws = self._wb[sheet_name] if sheet_name in self._wb.sheetnames else None
        if ws is None:
            return []
        return _read_sheet_rows(ws)

    def _add_error(self, sheet: str, row: int, message: str) -> None:
        self._errors.append({"sheet": sheet, "row": row, "message": message})

    def _validate_sheet(self, sheet_name: str, rows: list[dict]) -> None:
        required = {"code"} if "code" in SHEET_COLUMNS[sheet_name] else set()
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


class CatalogImportApplier:
    """Apply a validated catalog workbook inside one transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = CatalogRepo(session)
        self._contractors: dict[str, Contractor] = {}
        self._units: dict[str, Unit] = {}
        self._stages: dict[str, Stage] = {}
        self._objects: dict[str, Object] = {}
        self._methods: dict[str, WorkMethod] = {}
        self._work_types: dict[str, WorkType] = {}

    async def apply(self, validator: CatalogImportValidator) -> CatalogImport:
        import_record = CatalogImport(
            filename="applied.xlsx",
            status="validated",
            summary_json=validator.preview,
            errors_json=validator.errors,
        )
        self._session.add(import_record)
        await self._session.flush()

        if not validator.validate()["valid"]:
            import_record.status = "failed"
            await self._session.commit()
            raise ValueError("Импорт содержит ошибки валидации")

        await self._load_existing()
        await self._apply_contractors(validator)
        await self._apply_units(validator)
        await self._apply_stages(validator)
        await self._apply_objects(validator)
        await self._apply_object_stages(validator)
        await self._apply_equipment(validator)
        await self._apply_work_types(validator)
        await self._apply_work_methods(validator)
        await self._apply_work_type_methods(validator)

        import_record.status = "applied"
        import_record.applied_at = sa.func.now()
        await self._session.commit()
        return import_record

    async def _load_existing(self) -> None:
        self._contractors = {
            c.code: c for c in (await self._session.execute(select(Contractor))).scalars()
        }
        self._units = {
            u.code: u for u in (await self._session.execute(select(Unit))).scalars()
        }
        self._stages = {
            s.code: s for s in (await self._session.execute(select(Stage))).scalars()
        }
        self._objects = {
            o.code: o for o in (await self._session.execute(select(Object))).scalars()
        }
        self._methods = {
            m.code: m for m in (await self._session.execute(select(WorkMethod))).scalars()
        }
        self._work_types = {
            wt.code: wt
            for wt in (await self._session.execute(select(WorkType))).scalars()
        }

    async def _apply_contractors(self, validator: CatalogImportValidator) -> None:
        for row in validator.iter_rows("Contractors"):
            code = _normalize_text(row.get("code"))
            name = _normalize_text(row.get("name"))
            active = _normalize_bool(row.get("active"))
            if not code or not name:
                continue
            contractor = await self._repo.get_or_create_contractor(code=code, name=name)
            contractor.active = active
            self._contractors[code] = contractor

    async def _apply_units(self, validator: CatalogImportValidator) -> None:
        for row in validator.iter_rows("Units"):
            code = _normalize_text(row.get("code"))
            name = _normalize_text(row.get("name"))
            symbol = _normalize_text(row.get("symbol"))
            active = _normalize_bool(row.get("active"))
            if not code or not name:
                continue
            unit = await self._repo.get_or_create_unit(code=code, name=name, symbol=symbol)
            unit.active = active
            self._units[code] = unit

    async def _apply_stages(self, validator: CatalogImportValidator) -> None:
        for row in validator.iter_rows("Stages"):
            code = _normalize_text(row.get("code"))
            name = _normalize_text(row.get("name"))
            active = _normalize_bool(row.get("active"))
            if not code or not name:
                continue
            stage = await self._repo.get_or_create_stage(code=code, name=name)
            stage.active = active
            self._stages[code] = stage

    async def _apply_objects(self, validator: CatalogImportValidator) -> None:
        for row in validator.iter_rows("Objects"):
            code = _normalize_text(row.get("code"))
            name = _normalize_text(row.get("name"))
            execution_method = _normalize_text(row.get("execution_method")) or None
            default_contractor_code = _normalize_text(row.get("default_contractor_code")) or None
            active = _normalize_bool(row.get("active"))
            if not code or not name:
                continue
            default_contractor_id = None
            if default_contractor_code:
                contractor = self._contractors.get(default_contractor_code)
                if contractor is None:
                    raise ValueError(f"Подрядчик '{default_contractor_code}' не найден")
                default_contractor_id = contractor.id
            obj = await self._repo.get_or_create_object(
                code=code,
                name=name,
                execution_method=execution_method,
                default_contractor_id=default_contractor_id,
            )
            obj.active = active
            self._objects[code] = obj

    async def _apply_object_stages(self, validator: CatalogImportValidator) -> None:
        for row in validator.iter_rows("ObjectStages"):
            object_code = _normalize_text(row.get("object_code"))
            stage_code = _normalize_text(row.get("stage_code"))
            _normalize_bool(row.get("active"))
            if not object_code or not stage_code:
                continue
            obj = self._objects.get(object_code)
            stage = self._stages.get(stage_code)
            if obj is None or stage is None:
                raise ValueError(
                    f"Связь объекта '{object_code}' и этапа '{stage_code}' невозможна"
                )
            await self._repo.ensure_object_stage(obj.id, stage.id)

    async def _apply_equipment(self, validator: CatalogImportValidator) -> None:
        for row in validator.iter_rows("Equipment"):
            code = _normalize_text(row.get("code"))
            name = _normalize_text(row.get("name"))
            default_unit_code = _normalize_text(row.get("default_unit_code"))
            active = _normalize_bool(row.get("active"))
            if not code or not name:
                continue
            unit_id = self._units.get(default_unit_code).id if default_unit_code else None
            equipment = await self._repo.get_or_create_equipment_type(
                code=code, name=name, default_unit_id=unit_id
            )
            equipment.active = active

    async def _apply_work_types(self, validator: CatalogImportValidator) -> None:
        for row in validator.iter_rows("WorkTypes"):
            code = _normalize_text(row.get("code"))
            name = _normalize_text(row.get("name"))
            default_unit_code = _normalize_text(row.get("default_unit_code"))
            active = _normalize_bool(row.get("active"))
            if not code or not name:
                continue
            unit_id = self._units.get(default_unit_code).id if default_unit_code else None
            work_type = await self._repo.get_or_create_work_type(
                code=code, name=name, default_unit_id=unit_id
            )
            work_type.active = active
            self._work_types[code] = work_type

    async def _apply_work_methods(self, validator: CatalogImportValidator) -> None:
        for row in validator.iter_rows("WorkMethods"):
            code = _normalize_text(row.get("code"))
            name = _normalize_text(row.get("name"))
            active = _normalize_bool(row.get("active"))
            if not code or not name:
                continue
            method = await self._repo.get_or_create_work_method(code=code, name=name)
            method.active = active
            self._methods[code] = method

    async def _apply_work_type_methods(self, validator: CatalogImportValidator) -> None:
        for row in validator.iter_rows("WorkTypeMethods"):
            work_type_code = _normalize_text(row.get("work_type_code"))
            work_method_code = _normalize_text(row.get("work_method_code"))
            if not work_type_code or not work_method_code:
                continue
            work_type = self._work_types.get(work_type_code)
            method = self._methods.get(work_method_code)
            if work_type is None or method is None:
                raise ValueError(
                    f"Связь вида работы '{work_type_code}' и способа '{work_method_code}' невозможна"
                )
            await self._repo.ensure_work_type_method(work_type.id, method.id)


async def export_catalogs(session: AsyncSession) -> BytesIO:
    """Export current catalogs to an .xlsx workbook."""
    wb = Workbook()
    wb.remove(wb.active)

    contractors = (
        await session.execute(select(Contractor).where(Contractor.active))
    ).scalars().all()
    units = (await session.execute(select(Unit).where(Unit.active))).scalars().all()
    stages = (await session.execute(select(Stage).where(Stage.active))).scalars().all()
    objects = (await session.execute(select(Object))).scalars().all()
    equipment = (
        await session.execute(select(EquipmentType).where(EquipmentType.active))
    ).scalars().all()
    work_types = (
        await session.execute(select(WorkType).where(WorkType.active))
    ).scalars().all()
    methods = (
        await session.execute(select(WorkMethod).where(WorkMethod.active))
    ).scalars().all()
    object_stages = (
        await session.execute(
            select(ObjectStage).where(ObjectStage.active)
        )
    ).scalars().all()
    work_type_methods = (
        await session.execute(
            select(WorkTypeMethod).where(WorkTypeMethod.active)
        )
    ).scalars().all()

    code_to_contractor = {c.id: c for c in contractors}
    code_to_unit = {u.id: u for u in units}
    code_to_stage = {s.id: s for s in stages}
    code_to_object = {o.id: o for o in objects}

    sheets_data = {
        "Contractors": [
            [c.code, c.name, int(c.active), c.sort_order or ""]
            for c in contractors
        ],
        "Units": [
            [u.code, u.name, u.symbol, int(u.active), u.sort_order or ""]
            for u in units
        ],
        "Stages": [
            [s.code, s.name, int(s.active), s.sort_order or ""]
            for s in stages
        ],
        "Objects": [
            [
                o.code,
                o.name,
                o.execution_method or "",
                code_to_contractor.get(o.default_contractor_id, Contractor(code="")).code,
                int(o.active),
                o.sort_order or "",
            ]
            for o in objects
        ],
        "ObjectStages": [
            [
                code_to_object.get(os.object_id, Object(code="")).code,
                code_to_stage.get(os.stage_id, Stage(code="")).code,
                int(os.active),
            ]
            for os in object_stages
        ],
        "Equipment": [
            [
                e.code,
                e.name,
                code_to_unit.get(e.default_unit_id, Unit(code="")).code,
                int(e.active),
                e.sort_order or "",
            ]
            for e in equipment
        ],
        "WorkTypes": [
            [
                wt.code,
                wt.name,
                code_to_unit.get(wt.default_unit_id, Unit(code="")).code,
                int(wt.active),
                wt.sort_order or "",
            ]
            for wt in work_types
        ],
        "WorkMethods": [
            [m.code, m.name, int(m.active), m.sort_order or ""]
            for m in methods
        ],
        "WorkTypeMethods": [
            [
                code_to_object.get(wtm.work_type_id, WorkType(code="")).code,
                code_to_object.get(wtm.work_method_id, WorkMethod(code="")).code,
                int(wtm.active),
            ]
            for wtm in work_type_methods
        ],
    }

    for sheet_name, rows in sheets_data.items():
        ws = wb.create_sheet(title=sheet_name)
        ws.append(SHEET_COLUMNS[sheet_name])
        for row in rows:
            ws.append(row)

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
