from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CatalogItemRequest(BaseModel):
    """Base fields for catalog create/update."""

    code: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    active: bool = True
    sort_order: int | None = None


class ObjectRequest(CatalogItemRequest):
    short_title: str | None = None
    full_title: str | None = None
    execution_method: Literal["own", "contractor"] | None = None
    default_contractor_id: int | None = None


class ObjectResponse(ObjectRequest):
    id: int

    model_config = ConfigDict(from_attributes=True)


class StageRequest(CatalogItemRequest):
    pass


class StageResponse(StageRequest):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ContractorRequest(CatalogItemRequest):
    pass


class ContractorResponse(ContractorRequest):
    id: int

    model_config = ConfigDict(from_attributes=True)


class UnitRequest(CatalogItemRequest):
    symbol: str = Field(..., min_length=1, max_length=16)


class UnitResponse(UnitRequest):
    id: int

    model_config = ConfigDict(from_attributes=True)


class EquipmentTypeRequest(CatalogItemRequest):
    default_unit_id: int | None = None


class EquipmentTypeResponse(EquipmentTypeRequest):
    id: int

    model_config = ConfigDict(from_attributes=True)


class WorkTypeRequest(CatalogItemRequest):
    default_unit_id: int | None = None


class WorkTypeResponse(WorkTypeRequest):
    id: int

    model_config = ConfigDict(from_attributes=True)


class WorkMethodRequest(CatalogItemRequest):
    pass


class WorkMethodResponse(WorkMethodRequest):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ObjectStageRequest(BaseModel):
    object_id: int
    stage_id: int
    active: bool = True


class ObjectStageResponse(ObjectStageRequest):
    id: int
    object_code: str
    stage_code: str

    model_config = ConfigDict(from_attributes=True)


class WorkTypeMethodRequest(BaseModel):
    work_type_id: int
    work_method_id: int
    active: bool = True


class WorkTypeMethodResponse(WorkTypeMethodRequest):
    id: int
    work_type_code: str
    work_method_code: str

    model_config = ConfigDict(from_attributes=True)


class AssignmentRequest(BaseModel):
    user_id: int
    object_id: int
    active_from: date
    active_to: date
    schedule_type: Literal["daily", "weekdays"] = "daily"
    active: bool = True


class AssignmentResponse(AssignmentRequest):
    id: int
    user_name: str
    object_code: str

    model_config = ConfigDict(from_attributes=True)


class UserAdminRequest(BaseModel):
    max_user_id: str = Field(..., min_length=1, max_length=64)
    full_name: str = Field(..., min_length=1, max_length=255)
    role: Literal["responsible", "manager", "admin"] = "responsible"
    active: bool = True


class UserAdminResponse(UserAdminRequest):
    id: int

    model_config = ConfigDict(from_attributes=True)
