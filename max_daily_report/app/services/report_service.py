from __future__ import annotations

import json
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalogs import (
    EquipmentType,
    Object,
    ObjectStage,
    Stage,
    Unit,
    WorkMethod,
    WorkType,
    WorkTypeMethod,
)
from app.models.contracts import Contract, ObjectContract
from app.models.reports import (
    DailyReport,
    OutboxEvent,
    ReportEquipment,
    ReportObligation,
    ReportWork,
    ResponsibleObjectAssignment,
)
from app.models.users import User
from app.schemas.reports import ReportCreateRequest

DEFAULT_LIMIT = 20
MAX_LIMIT = 50


class ReportValidationError(ValueError):
    pass


class ReportDuplicateError(ValueError):
    """A report for this date/object/user already exists."""


class ReportService:
    """Create daily reports with invariants, idempotency and outbox event."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        user: User,
        data: ReportCreateRequest,
        idempotency_key: str,
    ) -> DailyReport:
        existing = await self._find_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing

        responsible = await self._resolve_responsible(user, data)

        obj = await self._get(Object, data.object_id)
        contract = None
        if data.contract_id is not None:
            contract = await self._get(Contract, data.contract_id)

        if data.contract_id is not None:
            # Подмена чужого/неактивного договора отклоняется.
            if contract is None or not contract.active:
                raise ReportValidationError(
                    "Указанный договор не привязан к объекту или неактивен"
                )
            link_result = await self._session.execute(
                select(ObjectContract).where(
                    ObjectContract.object_id == data.object_id,
                    ObjectContract.contract_id == data.contract_id,
                    ObjectContract.active.is_(True),
                )
            )
            if link_result.scalar_one_or_none() is None:
                raise ReportValidationError(
                    "Указанный договор не привязан к объекту или неактивен"
                )
        else:
            # Ровно один активный договор определяется автоматически. При двух
            # и более пользователь обязан выбрать договор явно: primary влияет
            # только на сортировку/подсказку, но не подменяет решение человека.
            mapping_result = await self._session.execute(
                select(ObjectContract).where(
                    ObjectContract.object_id == data.object_id,
                    ObjectContract.active.is_(True),
                )
            )
            mappings = list(mapping_result.scalars().all())
            if len(mappings) == 1:
                data.contract_id = mappings[0].contract_id
                contract = await self._get(Contract, data.contract_id)
            elif len(mappings) > 1:
                raise ReportValidationError(
                    "Выберите договор для объекта с несколькими договорами"
                )

        await self._validate(responsible, data)

        report = DailyReport(
            report_date=data.report_date,
            responsible_user_id=responsible.id,
            object_id=data.object_id,
            stage_id=data.stage_id,
            contractor_id=data.contractor_id,
            contract_id=data.contract_id,
            object_name_snapshot=(obj.full_title or obj.short_title or obj.name) if obj else "",
            contract_code_snapshot=contract.code if contract else None,
            contract_full_name_snapshot=contract.full_name if contract else None,
            comment=data.comment,
            staff_itr=data.staff.itr,
            staff_internal=data.staff.internal,
            staff_external=data.staff.external,
            soil_export_m3=data.soil_export_m3,
            status="submitted",
            idempotency_key=idempotency_key,
        )
        self._session.add(report)
        await self._session.flush()

        for eq_input in data.equipment:
            equipment_type = await self._get(EquipmentType, eq_input.equipment_type_id)
            if equipment_type is None:
                raise ReportValidationError("equipment type not found")
            unit = await self._get(Unit, eq_input.unit_id)
            if unit is None:
                raise ReportValidationError("unit not found")
            self._session.add(
                ReportEquipment(
                    report_id=report.id,
                    equipment_type_id=equipment_type.id,
                    equipment_name_snapshot=equipment_type.name,
                    ownership=eq_input.ownership,
                    unit_id=unit.id,
                    unit_name_snapshot=unit.symbol or unit.name,
                    quantity=eq_input.quantity,
                    comment=eq_input.comment,
                )
            )

        for work_input in data.works:
            work_type = await self._get(WorkType, work_input.work_type_id)
            if work_type is None:
                raise ReportValidationError("work type not found")
            unit = await self._get(Unit, work_input.unit_id)
            if unit is None:
                raise ReportValidationError("unit not found")
            method = None
            if work_input.work_method_id:
                method = await self._get(WorkMethod, work_input.work_method_id)
                if method is None:
                    raise ReportValidationError("work method not found")
                await self._validate_work_method(work_type.id, method.id)
            self._session.add(
                ReportWork(
                    report_id=report.id,
                    work_type_id=work_type.id,
                    work_name_snapshot=work_type.name,
                    work_method_id=method.id if method else None,
                    method_name_snapshot=method.name if method else None,
                    unit_id=unit.id,
                    unit_name_snapshot=unit.symbol or unit.name,
                    quantity=work_input.quantity,
                    comment=work_input.comment,
                )
            )

        await self._update_obligation(report, responsible.id)
        await self._create_outbox_event(report)
        await self._session.commit()
        return report

    async def _resolve_responsible(
        self, user: User, data: ReportCreateRequest
    ) -> User:
        """Отчёт пишется на автора; подмена — только для manager/admin."""
        if data.responsible_user_id is None or data.responsible_user_id == user.id:
            return user
        if user.role not in ("manager", "admin"):
            raise ReportValidationError(
                "Подмена ответственного доступна только руководителю"
            )
        target = await self._get(User, data.responsible_user_id)
        if target is None or not target.active:
            raise ReportValidationError("responsible user not found")
        return target

    async def list_reports(
        self,
        user: User,
        date_from: date | None,
        date_to: date | None,
        object_id: int | None,
        responsible_user_id: int | None,
        limit: int,
        offset: int,
    ) -> tuple[list[DailyReport], int]:
        limit = max(1, min(limit, MAX_LIMIT))
        offset = max(0, offset)
        stmt = select(DailyReport)
        if user.role == "responsible":
            stmt = stmt.where(DailyReport.responsible_user_id == user.id)
        if date_from is not None:
            stmt = stmt.where(DailyReport.report_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(DailyReport.report_date <= date_to)
        if object_id is not None:
            stmt = stmt.where(DailyReport.object_id == object_id)
        if responsible_user_id is not None and user.role in ("manager", "admin"):
            stmt = stmt.where(DailyReport.responsible_user_id == responsible_user_id)
        stmt = stmt.order_by(DailyReport.report_date.desc(), DailyReport.id.desc())
        total_result = await self._session.execute(
            select(func.count()).select_from(stmt.subquery())
        )
        total = total_result.scalar() or 0
        result = await self._session.execute(stmt.limit(limit).offset(offset))
        return list(result.scalars().all()), total

    async def submission_status(
        self,
        user: User,
        target_date: date,
    ) -> dict:
        obligations_stmt = (
            select(ReportObligation, User.full_name, Object.code)
            .join(User, ReportObligation.user_id == User.id)
            .join(Object, ReportObligation.object_id == Object.id)
            .where(ReportObligation.report_date == target_date)
        )
        if user.role == "responsible":
            obligations_stmt = obligations_stmt.where(
                ReportObligation.user_id == user.id
            )
        result = await self._session.execute(obligations_stmt)
        rows = result.all()

        expected = len(rows)
        submitted = sum(1 for o, _, _ in rows if o.status == "submitted")
        late = sum(1 for o, _, _ in rows if o.status == "late")
        pending = sum(1 for o, _, _ in rows if o.status == "pending")
        missing = [
            {"responsible": full_name, "object_code": object_code}
            for o, full_name, object_code in rows
            if o.status in ("pending", "missed")
        ]
        return {
            "expected": expected,
            "submitted": submitted,
            "late": late,
            "pending": pending,
            "missing": missing,
        }

    async def _find_by_idempotency_key(self, key: str) -> DailyReport | None:
        result = await self._session.execute(
            select(DailyReport).where(DailyReport.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    async def _validate(self, user: User, data: ReportCreateRequest) -> None:
        obj = await self._get(Object, data.object_id)
        if obj is None:
            raise ReportValidationError("object not found")
        if not obj.active:
            raise ReportValidationError("object is inactive")

        stage = await self._get(Stage, data.stage_id)
        if stage is None:
            raise ReportValidationError("stage not found")

        # stage must belong to object
        link = await self._session.execute(
            select(ObjectStage).where(
                ObjectStage.object_id == data.object_id,
                ObjectStage.stage_id == data.stage_id,
                ObjectStage.active.is_(True),
            )
        )
        if link.scalar_one_or_none() is None:
            raise ReportValidationError("stage is not linked to object")

        # contractor object requires contractor
        if obj.execution_method == "contractor" and data.contractor_id is None:
            raise ReportValidationError("contractor_id required for contractor object")

        # contract must be active and linked to the object (O04 preliminary check)
        if data.contract_id is not None:
            contract = await self._get(Contract, data.contract_id)
            if contract is None or not contract.active:
                raise ReportValidationError("Указанный договор не привязан к объекту")
            link = await self._session.execute(
                select(ObjectContract).where(
                    ObjectContract.object_id == data.object_id,
                    ObjectContract.contract_id == data.contract_id,
                    ObjectContract.active.is_(True),
                )
            )
            if link.scalar_one_or_none() is None:
                raise ReportValidationError("Указанный договор не привязан к объекту")

        # user must have active assignment for object on report date
        assignment_result = await self._session.execute(
            select(ResponsibleObjectAssignment).where(
                ResponsibleObjectAssignment.user_id == user.id,
                ResponsibleObjectAssignment.object_id == data.object_id,
                ResponsibleObjectAssignment.active.is_(True),
                ResponsibleObjectAssignment.active_from <= data.report_date,
                ResponsibleObjectAssignment.active_to >= data.report_date,
            )
        )
        if assignment_result.scalar_one_or_none() is None:
            raise ReportValidationError("no active assignment for this object and date")

        # at least one value present (staff counts only if > 0)
        has_staff = (
            data.staff.itr > 0
            or data.staff.internal > 0
            or data.staff.external > 0
        )
        has_equipment = bool(data.equipment)
        has_works = bool(data.works)
        has_soil = data.soil_export_m3 is not None and data.soil_export_m3 > 0
        if not (has_staff or has_equipment or has_works or has_soil):
            raise ReportValidationError(
                "report must contain equipment, works, soil_export or staff"
            )

        for eq_input in data.equipment:
            if eq_input.quantity <= 0:
                raise ReportValidationError("equipment quantity must be > 0")
        for work_input in data.works:
            if work_input.quantity <= 0:
                raise ReportValidationError("work quantity must be > 0")

    async def _validate_work_method(
        self, work_type_id: int, work_method_id: int
    ) -> None:
        result = await self._session.execute(
            select(WorkTypeMethod).where(
                WorkTypeMethod.work_type_id == work_type_id,
                WorkTypeMethod.work_method_id == work_method_id,
                WorkTypeMethod.active.is_(True),
            )
        )
        if result.scalar_one_or_none() is None:
            raise ReportValidationError("work method is not allowed for work type")

    async def _update_obligation(self, report: DailyReport, user_id: int) -> None:
        result = await self._session.execute(
            select(ReportObligation)
            .where(
                ReportObligation.report_date == report.report_date,
                ReportObligation.user_id == user_id,
                ReportObligation.object_id == report.object_id,
            )
            .with_for_update(skip_locked=True)
        )
        obligation = result.scalar_one_or_none()
        now = datetime.now(UTC)
        if obligation is not None and obligation.status in ("submitted", "late"):
            raise ReportDuplicateError(
                "Отчёт за эту дату по этому объекту уже сдан"
            )
        if obligation is None:
            # create orphan obligation if none existed
            assignment_result = await self._session.execute(
                select(ResponsibleObjectAssignment).where(
                    ResponsibleObjectAssignment.user_id == user_id,
                    ResponsibleObjectAssignment.object_id == report.object_id,
                    ResponsibleObjectAssignment.active.is_(True),
                    ResponsibleObjectAssignment.active_from <= report.report_date,
                    ResponsibleObjectAssignment.active_to >= report.report_date,
                )
            )
            assignment = assignment_result.scalar_one_or_none()
            if assignment is None:
                raise ReportValidationError(
                    "no active assignment for this object and date"
                )
            obligation = ReportObligation(
                report_date=report.report_date,
                assignment_id=assignment.id,
                user_id=user_id,
                object_id=report.object_id,
                status="submitted",
                submitted_at=now,
                report_id=report.id,
            )
            self._session.add(obligation)
        else:
            # сдача после дедлайна фиксируется как late (спека 15_group_bot)
            is_late = obligation.due_at is not None and now > obligation.due_at
            obligation.status = "late" if is_late else "submitted"
            obligation.submitted_at = now
            obligation.report_id = report.id
        await self._session.flush()

    async def _create_outbox_event(self, report: DailyReport) -> None:
        result = await self._session.execute(
            select(OutboxEvent).where(OutboxEvent.event_key == f"report_submitted:{report.id}")
        )
        if result.scalar_one_or_none() is not None:
            return
        event = OutboxEvent(
            event_key=f"report_submitted:{report.id}",
            kind="report_submitted",
            payload_json=json.dumps(
                {
                    "report_id": report.id,
                    "object_id": report.object_id,
                    "responsible_user_id": report.responsible_user_id,
                    "report_date": report.report_date.isoformat(),
                }
            ),
            status="pending",
        )
        self._session.add(event)
        await self._session.flush()

    async def _get(self, model_cls, ident: int | None):
        if ident is None:
            return None
        result = await self._session.execute(
            select(model_cls).where(model_cls.id == ident)
        )
        return result.scalar_one_or_none()


async def create_report(
    session: AsyncSession,
    user: User,
    data: ReportCreateRequest,
    idempotency_key: str,
) -> DailyReport:
    service = ReportService(session)
    return await service.create(user, data, idempotency_key)
