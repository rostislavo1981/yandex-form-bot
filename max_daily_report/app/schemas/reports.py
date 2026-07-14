from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StaffInput(BaseModel):
    itr: int = 0
    internal: int = 0
    external: int = 0


class EquipmentInput(BaseModel):
    equipment_type_id: int
    ownership: str = Field(pattern=r"^(own|rented|contractor)$")
    unit_id: int
    quantity: Decimal
    comment: str | None = None

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("quantity must be > 0")
        return value


class WorkInput(BaseModel):
    work_type_id: int
    work_method_id: int | None = None
    unit_id: int
    quantity: Decimal
    comment: str | None = None

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("quantity must be > 0")
        return value


class ReportCreateRequest(BaseModel):
    report_date: date
    object_id: int
    stage_id: int
    contractor_id: int | None = None
    staff: StaffInput = Field(default_factory=StaffInput)
    soil_export_m3: Decimal | None = None
    equipment: list[EquipmentInput] = Field(default_factory=list)
    works: list[WorkInput] = Field(default_factory=list)
    comment: str | None = None

    @field_validator("equipment", "works")
    @classmethod
    def at_least_one_detail(cls, value: list, info) -> list:
        all_values = info.data
        has_equipment = bool(all_values.get("equipment"))
        has_works = bool(all_values.get("works"))
        has_soil = all_values.get("soil_export_m3") is not None
        has_staff = bool(
            (all_values.get("staff") or StaffInput()).itr
            or (all_values.get("staff") or StaffInput()).internal
            or (all_values.get("staff") or StaffInput()).external
        )
        if not (has_equipment or has_works or has_soil or has_staff):
            raise ValueError("report must contain equipment, works, soil_export or staff")
        return value


class ReportCreatedResponse(BaseModel):
    id: int
    status: str
    late: bool

    model_config = ConfigDict(from_attributes=True)


class ReportEquipmentResponse(BaseModel):
    id: int
    equipment_type_id: int
    equipment_name_snapshot: str
    ownership: str
    unit_id: int
    unit_name_snapshot: str
    quantity: Decimal
    comment: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ReportWorkResponse(BaseModel):
    id: int
    work_type_id: int
    work_name_snapshot: str
    work_method_id: int | None
    method_name_snapshot: str | None
    unit_id: int
    unit_name_snapshot: str
    quantity: Decimal
    comment: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ReportDetailResponse(BaseModel):
    id: int
    report_date: date
    object_id: int
    stage_id: int
    contractor_id: int | None
    staff_itr: int
    staff_internal: int
    staff_external: int
    soil_export_m3: Decimal | None
    comment: str | None
    status: str
    equipment: list[ReportEquipmentResponse]
    works: list[ReportWorkResponse]

    model_config = ConfigDict(from_attributes=True)


class ReportListResponse(BaseModel):
    items: list[ReportDetailResponse]
    total: int


class MissingReportItem(BaseModel):
    responsible: str
    object_code: str


class SubmissionStatusResponse(BaseModel):
    expected: int
    submitted: int
    late: int
    pending: int
    missing: list[MissingReportItem]
