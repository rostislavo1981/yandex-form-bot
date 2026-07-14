from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.catalogs import Object
from app.models.reports import DailyReport, ReportObligation


@dataclass(frozen=True)
class _RowKey:
    category: str
    item_name: str
    ownership_or_method: str
    unit_name: str


@dataclass
class _Row:
    key: _RowKey
    values: dict[date, Decimal] = field(default_factory=dict)


class TimesheetService:
    """Build an object-level timesheet for a date range."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def build(
        self,
        object_id: int,
        date_from: date,
        date_to: date,
    ) -> dict[str, Any]:
        obj = await self._session.get(Object, object_id)
        if obj is None:
            raise ValueError("object not found")

        if date_to < date_from:
            date_to = date_from

        reports = await self._load_reports(object_id, date_from, date_to)
        obligations = await self._load_obligations(object_id, date_from, date_to)
        days = self._date_range(date_from, date_to)

        personnel_row = _Row(key=_RowKey("personnel", "Персонал", "", "чел"))
        equipment_rows: dict[_RowKey, _Row] = {}
        work_rows: dict[_RowKey, _Row] = {}
        soil_row = _Row(key=_RowKey("soil", "Вывоз грунта", "", "м³"))
        submitted_days: set[date] = set()

        for report in reports:
            submitted_days.add(report.report_date)
            personnel_row.values[report.report_date] = Decimal(
                report.staff_itr + report.staff_internal + report.staff_external
            )
            if report.soil_export_m3:
                soil_row.values[report.report_date] = report.soil_export_m3
            for eq in report.equipment:
                key = _RowKey(
                    "equipment",
                    eq.equipment_name_snapshot,
                    eq.ownership,
                    eq.unit_name_snapshot,
                )
                row = equipment_rows.setdefault(key, _Row(key))
                row.values[report.report_date] = row.values.get(report.report_date, Decimal(0)) + eq.quantity
            for w in report.works:
                method = w.method_name_snapshot or ""
                key = _RowKey("work", w.work_name_snapshot, method, w.unit_name_snapshot)
                row = work_rows.setdefault(key, _Row(key))
                row.values[report.report_date] = row.values.get(report.report_date, Decimal(0)) + w.quantity

        expected_days = {o.report_date for o in obligations}
        missing_days = expected_days - submitted_days

        rows = []
        if personnel_row.values:
            rows.append(self._render_row(personnel_row, days, expected_days))
        if soil_row.values:
            rows.append(self._render_row(soil_row, days, expected_days))
        for row in equipment_rows.values():
            rows.append(self._render_row(row, days, expected_days))
        for row in work_rows.values():
            rows.append(self._render_row(row, days, expected_days))

        return {
            "object_id": object_id,
            "object_code": obj.code,
            "object_name": obj.name,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "days": [d.isoformat() for d in days],
            "rows": rows,
            "missing_days": sorted(d.isoformat() for d in missing_days),
        }

    async def _load_reports(
        self,
        object_id: int,
        date_from: date,
        date_to: date,
    ) -> list[DailyReport]:
        result = await self._session.execute(
            select(DailyReport)
            .where(DailyReport.object_id == object_id)
            .where(DailyReport.report_date >= date_from)
            .where(DailyReport.report_date <= date_to)
            .options(selectinload(DailyReport.equipment), selectinload(DailyReport.works))
            .order_by(DailyReport.report_date)
        )
        return list(result.scalars().all())

    async def _load_obligations(
        self,
        object_id: int,
        date_from: date,
        date_to: date,
    ) -> list[ReportObligation]:
        result = await self._session.execute(
            select(ReportObligation)
            .where(ReportObligation.object_id == object_id)
            .where(ReportObligation.report_date >= date_from)
            .where(ReportObligation.report_date <= date_to)
        )
        return list(result.scalars().all())

    @staticmethod
    def _date_range(date_from: date, date_to: date) -> list[date]:
        days = []
        current = date_from
        while current <= date_to:
            days.append(current)
            current += timedelta(days=1)
        return days

    def _render_row(
        self,
        row: _Row,
        days: list[date],
        expected_days: set[date],
    ) -> dict[str, Any]:
        values: list[Decimal | str | None] = []
        total = Decimal(0)
        max_value = Decimal(0)
        count = 0
        for d in days:
            if d in row.values:
                value = row.values[d]
                values.append(value)
                total += value
                if value > max_value:
                    max_value = value
                count += 1
            elif d in expected_days:
                values.append(None)  # missing expected report
            else:
                values.append(Decimal(0))
        avg = total / Decimal(count) if count else Decimal(0)
        return {
            "category": row.key.category,
            "item_name": row.key.item_name,
            "ownership_or_method": row.key.ownership_or_method,
            "unit": row.key.unit_name,
            "values": [self._format(v) for v in values],
            "total": self._format(total),
            "average": self._format(avg),
            "max": self._format(max_value),
        }

    @staticmethod
    def _format(value: Decimal | None) -> str:
        if value is None:
            return ""
        if value == value.to_integral_value():
            return str(int(value))
        return str(value.normalize())
