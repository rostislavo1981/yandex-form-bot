from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.deps import get_session, require_user
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
from app.models.reports import ResponsibleObjectAssignment
from app.models.users import User
from app.schemas.admin_catalogs import (
    AssignmentRequest,
    AssignmentResponse,
    ContractorRequest,
    ContractorResponse,
    EquipmentTypeRequest,
    EquipmentTypeResponse,
    ObjectRequest,
    ObjectResponse,
    ObjectStageRequest,
    ObjectStageResponse,
    StageRequest,
    StageResponse,
    UnitRequest,
    UnitResponse,
    UserAdminRequest,
    UserAdminResponse,
    WorkMethodRequest,
    WorkMethodResponse,
    WorkTypeMethodRequest,
    WorkTypeMethodResponse,
    WorkTypeRequest,
    WorkTypeResponse,
)

router = APIRouter(
    prefix="/api/admin/catalogs",
    tags=["admin-catalogs"],
    dependencies=[Depends(require_user)],
)


def _extract_user(request: Request) -> User:
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user


def _require_manager(user: User) -> None:
    if user.role not in ("manager", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="insufficient role",
        )


@router.get("/objects", response_model=list[ObjectResponse])
async def list_objects(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> list[ObjectResponse]:
    _require_manager(_extract_user(request))
    result = await session.execute(select(Object).order_by(Object.sort_order, Object.name))
    return [ObjectResponse.model_validate(obj) for obj in result.scalars().all()]


@router.post("/objects", response_model=ObjectResponse, status_code=status.HTTP_201_CREATED)
async def create_object(
    request: Request,
    data: ObjectRequest,
    session: AsyncSession = Depends(get_session),
) -> ObjectResponse:
    _require_manager(_extract_user(request))
    existing = await session.execute(select(Object).where(Object.code == data.code))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="object code already exists",
        )
    obj = Object(
        code=data.code,
        name=data.name,
        execution_method=data.execution_method,
        default_contractor_id=data.default_contractor_id,
        active=data.active,
        sort_order=data.sort_order,
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return ObjectResponse.model_validate(obj)


@router.put("/objects/{object_id}", response_model=ObjectResponse)
async def update_object(
    object_id: int,
    request: Request,
    data: ObjectRequest,
    session: AsyncSession = Depends(get_session),
) -> ObjectResponse:
    _require_manager(_extract_user(request))
    result = await session.execute(select(Object).where(Object.id == object_id))
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="object not found",
        )
    if data.code != obj.code:
        existing = await session.execute(
            select(Object).where(Object.code == data.code, Object.id != object_id)
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="object code already exists",
            )
    obj.code = data.code
    obj.name = data.name
    obj.execution_method = data.execution_method
    obj.default_contractor_id = data.default_contractor_id
    obj.active = data.active
    obj.sort_order = data.sort_order
    await session.commit()
    await session.refresh(obj)
    return ObjectResponse.model_validate(obj)


@router.delete("/objects/{object_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_object(
    object_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> None:
    _require_manager(_extract_user(request))
    result = await session.execute(select(Object).where(Object.id == object_id))
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="object not found",
        )
    obj.active = False
    await session.commit()


@router.get("/stages", response_model=list[StageResponse])
async def list_stages(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> list[StageResponse]:
    _require_manager(_extract_user(request))
    result = await session.execute(select(Stage).order_by(Stage.sort_order, Stage.name))
    return [StageResponse.model_validate(stage) for stage in result.scalars().all()]


@router.post("/stages", response_model=StageResponse, status_code=status.HTTP_201_CREATED)
async def create_stage(
    request: Request,
    data: StageRequest,
    session: AsyncSession = Depends(get_session),
) -> StageResponse:
    _require_manager(_extract_user(request))
    existing = await session.execute(select(Stage).where(Stage.code == data.code))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="stage code already exists",
        )
    stage = Stage(
        code=data.code,
        name=data.name,
        active=data.active,
        sort_order=data.sort_order,
    )
    session.add(stage)
    await session.commit()
    await session.refresh(stage)
    return StageResponse.model_validate(stage)


@router.put("/stages/{stage_id}", response_model=StageResponse)
async def update_stage(
    stage_id: int,
    request: Request,
    data: StageRequest,
    session: AsyncSession = Depends(get_session),
) -> StageResponse:
    _require_manager(_extract_user(request))
    result = await session.execute(select(Stage).where(Stage.id == stage_id))
    stage = result.scalar_one_or_none()
    if stage is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="stage not found",
        )
    if data.code != stage.code:
        existing = await session.execute(
            select(Stage).where(Stage.code == data.code, Stage.id != stage_id)
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="stage code already exists",
            )
    stage.code = data.code
    stage.name = data.name
    stage.active = data.active
    stage.sort_order = data.sort_order
    await session.commit()
    await session.refresh(stage)
    return StageResponse.model_validate(stage)


@router.delete("/stages/{stage_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stage(
    stage_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> None:
    _require_manager(_extract_user(request))
    result = await session.execute(select(Stage).where(Stage.id == stage_id))
    stage = result.scalar_one_or_none()
    if stage is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="stage not found",
        )
    stage.active = False
    await session.commit()


@router.get("/contractors", response_model=list[ContractorResponse])
async def list_contractors(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> list[ContractorResponse]:
    _require_manager(_extract_user(request))
    result = await session.execute(
        select(Contractor).order_by(Contractor.sort_order, Contractor.name)
    )
    return [ContractorResponse.model_validate(c) for c in result.scalars().all()]


@router.post(
    "/contractors", response_model=ContractorResponse, status_code=status.HTTP_201_CREATED
)
async def create_contractor(
    request: Request,
    data: ContractorRequest,
    session: AsyncSession = Depends(get_session),
) -> ContractorResponse:
    _require_manager(_extract_user(request))
    existing = await session.execute(select(Contractor).where(Contractor.code == data.code))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="contractor code already exists",
        )
    contractor = Contractor(
        code=data.code,
        name=data.name,
        active=data.active,
        sort_order=data.sort_order,
    )
    session.add(contractor)
    await session.commit()
    await session.refresh(contractor)
    return ContractorResponse.model_validate(contractor)


@router.put("/contractors/{contractor_id}", response_model=ContractorResponse)
async def update_contractor(
    contractor_id: int,
    request: Request,
    data: ContractorRequest,
    session: AsyncSession = Depends(get_session),
) -> ContractorResponse:
    _require_manager(_extract_user(request))
    result = await session.execute(select(Contractor).where(Contractor.id == contractor_id))
    contractor = result.scalar_one_or_none()
    if contractor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="contractor not found",
        )
    if data.code != contractor.code:
        existing = await session.execute(
            select(Contractor).where(
                Contractor.code == data.code, Contractor.id != contractor_id
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="contractor code already exists",
            )
    contractor.code = data.code
    contractor.name = data.name
    contractor.active = data.active
    contractor.sort_order = data.sort_order
    await session.commit()
    await session.refresh(contractor)
    return ContractorResponse.model_validate(contractor)


@router.delete("/contractors/{contractor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contractor(
    contractor_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> None:
    _require_manager(_extract_user(request))
    result = await session.execute(select(Contractor).where(Contractor.id == contractor_id))
    contractor = result.scalar_one_or_none()
    if contractor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="contractor not found",
        )
    contractor.active = False
    await session.commit()


@router.get("/units", response_model=list[UnitResponse])
async def list_units(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> list[UnitResponse]:
    _require_manager(_extract_user(request))
    result = await session.execute(select(Unit).order_by(Unit.sort_order, Unit.name))
    return [UnitResponse.model_validate(u) for u in result.scalars().all()]


@router.post("/units", response_model=UnitResponse, status_code=status.HTTP_201_CREATED)
async def create_unit(
    request: Request,
    data: UnitRequest,
    session: AsyncSession = Depends(get_session),
) -> UnitResponse:
    _require_manager(_extract_user(request))
    existing = await session.execute(select(Unit).where(Unit.code == data.code))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="unit code already exists",
        )
    unit = Unit(
        code=data.code,
        name=data.name,
        symbol=data.symbol,
        active=data.active,
        sort_order=data.sort_order,
    )
    session.add(unit)
    await session.commit()
    await session.refresh(unit)
    return UnitResponse.model_validate(unit)


@router.put("/units/{unit_id}", response_model=UnitResponse)
async def update_unit(
    unit_id: int,
    request: Request,
    data: UnitRequest,
    session: AsyncSession = Depends(get_session),
) -> UnitResponse:
    _require_manager(_extract_user(request))
    result = await session.execute(select(Unit).where(Unit.id == unit_id))
    unit = result.scalar_one_or_none()
    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="unit not found",
        )
    if data.code != unit.code:
        existing = await session.execute(
            select(Unit).where(Unit.code == data.code, Unit.id != unit_id)
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="unit code already exists",
            )
    unit.code = data.code
    unit.name = data.name
    unit.symbol = data.symbol
    unit.active = data.active
    unit.sort_order = data.sort_order
    await session.commit()
    await session.refresh(unit)
    return UnitResponse.model_validate(unit)


@router.delete("/units/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_unit(
    unit_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> None:
    _require_manager(_extract_user(request))
    result = await session.execute(select(Unit).where(Unit.id == unit_id))
    unit = result.scalar_one_or_none()
    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="unit not found",
        )
    unit.active = False
    await session.commit()


@router.get("/equipment", response_model=list[EquipmentTypeResponse])
async def list_equipment(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> list[EquipmentTypeResponse]:
    _require_manager(_extract_user(request))
    result = await session.execute(
        select(EquipmentType).order_by(EquipmentType.sort_order, EquipmentType.name)
    )
    return [EquipmentTypeResponse.model_validate(e) for e in result.scalars().all()]


@router.post(
    "/equipment", response_model=EquipmentTypeResponse, status_code=status.HTTP_201_CREATED
)
async def create_equipment(
    request: Request,
    data: EquipmentTypeRequest,
    session: AsyncSession = Depends(get_session),
) -> EquipmentTypeResponse:
    _require_manager(_extract_user(request))
    existing = await session.execute(
        select(EquipmentType).where(EquipmentType.code == data.code)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="equipment code already exists",
        )
    equipment = EquipmentType(
        code=data.code,
        name=data.name,
        default_unit_id=data.default_unit_id,
        active=data.active,
        sort_order=data.sort_order,
    )
    session.add(equipment)
    await session.commit()
    await session.refresh(equipment)
    return EquipmentTypeResponse.model_validate(equipment)


@router.put("/equipment/{equipment_id}", response_model=EquipmentTypeResponse)
async def update_equipment(
    equipment_id: int,
    request: Request,
    data: EquipmentTypeRequest,
    session: AsyncSession = Depends(get_session),
) -> EquipmentTypeResponse:
    _require_manager(_extract_user(request))
    result = await session.execute(
        select(EquipmentType).where(EquipmentType.id == equipment_id)
    )
    equipment = result.scalar_one_or_none()
    if equipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="equipment not found",
        )
    if data.code != equipment.code:
        existing = await session.execute(
            select(EquipmentType).where(
                EquipmentType.code == data.code, EquipmentType.id != equipment_id
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="equipment code already exists",
            )
    equipment.code = data.code
    equipment.name = data.name
    equipment.default_unit_id = data.default_unit_id
    equipment.active = data.active
    equipment.sort_order = data.sort_order
    await session.commit()
    await session.refresh(equipment)
    return EquipmentTypeResponse.model_validate(equipment)


@router.delete("/equipment/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_equipment(
    equipment_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> None:
    _require_manager(_extract_user(request))
    result = await session.execute(
        select(EquipmentType).where(EquipmentType.id == equipment_id)
    )
    equipment = result.scalar_one_or_none()
    if equipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="equipment not found",
        )
    equipment.active = False
    await session.commit()


@router.get("/work-types", response_model=list[WorkTypeResponse])
async def list_work_types(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> list[WorkTypeResponse]:
    _require_manager(_extract_user(request))
    result = await session.execute(
        select(WorkType).order_by(WorkType.sort_order, WorkType.name)
    )
    return [WorkTypeResponse.model_validate(wt) for wt in result.scalars().all()]


@router.post(
    "/work-types", response_model=WorkTypeResponse, status_code=status.HTTP_201_CREATED
)
async def create_work_type(
    request: Request,
    data: WorkTypeRequest,
    session: AsyncSession = Depends(get_session),
) -> WorkTypeResponse:
    _require_manager(_extract_user(request))
    existing = await session.execute(select(WorkType).where(WorkType.code == data.code))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="work type code already exists",
        )
    work_type = WorkType(
        code=data.code,
        name=data.name,
        default_unit_id=data.default_unit_id,
        active=data.active,
        sort_order=data.sort_order,
    )
    session.add(work_type)
    await session.commit()
    await session.refresh(work_type)
    return WorkTypeResponse.model_validate(work_type)


@router.put("/work-types/{work_type_id}", response_model=WorkTypeResponse)
async def update_work_type(
    work_type_id: int,
    request: Request,
    data: WorkTypeRequest,
    session: AsyncSession = Depends(get_session),
) -> WorkTypeResponse:
    _require_manager(_extract_user(request))
    result = await session.execute(select(WorkType).where(WorkType.id == work_type_id))
    work_type = result.scalar_one_or_none()
    if work_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="work type not found",
        )
    if data.code != work_type.code:
        existing = await session.execute(
            select(WorkType).where(
                WorkType.code == data.code, WorkType.id != work_type_id
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="work type code already exists",
            )
    work_type.code = data.code
    work_type.name = data.name
    work_type.default_unit_id = data.default_unit_id
    work_type.active = data.active
    work_type.sort_order = data.sort_order
    await session.commit()
    await session.refresh(work_type)
    return WorkTypeResponse.model_validate(work_type)


@router.delete("/work-types/{work_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_work_type(
    work_type_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> None:
    _require_manager(_extract_user(request))
    result = await session.execute(select(WorkType).where(WorkType.id == work_type_id))
    work_type = result.scalar_one_or_none()
    if work_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="work type not found",
        )
    work_type.active = False
    await session.commit()


@router.get("/work-methods", response_model=list[WorkMethodResponse])
async def list_work_methods(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> list[WorkMethodResponse]:
    _require_manager(_extract_user(request))
    result = await session.execute(
        select(WorkMethod).order_by(WorkMethod.sort_order, WorkMethod.name)
    )
    return [WorkMethodResponse.model_validate(m) for m in result.scalars().all()]


@router.post(
    "/work-methods", response_model=WorkMethodResponse, status_code=status.HTTP_201_CREATED
)
async def create_work_method(
    request: Request,
    data: WorkMethodRequest,
    session: AsyncSession = Depends(get_session),
) -> WorkMethodResponse:
    _require_manager(_extract_user(request))
    existing = await session.execute(
        select(WorkMethod).where(WorkMethod.code == data.code)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="work method code already exists",
        )
    method = WorkMethod(
        code=data.code,
        name=data.name,
        active=data.active,
        sort_order=data.sort_order,
    )
    session.add(method)
    await session.commit()
    await session.refresh(method)
    return WorkMethodResponse.model_validate(method)


@router.put("/work-methods/{work_method_id}", response_model=WorkMethodResponse)
async def update_work_method(
    work_method_id: int,
    request: Request,
    data: WorkMethodRequest,
    session: AsyncSession = Depends(get_session),
) -> WorkMethodResponse:
    _require_manager(_extract_user(request))
    result = await session.execute(select(WorkMethod).where(WorkMethod.id == work_method_id))
    method = result.scalar_one_or_none()
    if method is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="work method not found",
        )
    if data.code != method.code:
        existing = await session.execute(
            select(WorkMethod).where(
                WorkMethod.code == data.code, WorkMethod.id != work_method_id
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="work method code already exists",
            )
    method.code = data.code
    method.name = data.name
    method.active = data.active
    method.sort_order = data.sort_order
    await session.commit()
    await session.refresh(method)
    return WorkMethodResponse.model_validate(method)


@router.delete("/work-methods/{work_method_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_work_method(
    work_method_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> None:
    _require_manager(_extract_user(request))
    result = await session.execute(select(WorkMethod).where(WorkMethod.id == work_method_id))
    method = result.scalar_one_or_none()
    if method is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="work method not found",
        )
    method.active = False
    await session.commit()


@router.get("/object-stages", response_model=list[ObjectStageResponse])
async def list_object_stages(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> list[ObjectStageResponse]:
    _require_manager(_extract_user(request))
    result = await session.execute(
        select(ObjectStage)
        .join(Object)
        .join(Stage)
        .order_by(Object.code, Stage.name)
        .options(selectinload(ObjectStage.object), selectinload(ObjectStage.stage))
    )
    rows = result.scalars().all()
    return [
        ObjectStageResponse(
            id=row.id,
            object_id=row.object_id,
            stage_id=row.stage_id,
            active=row.active,
            object_code=row.object.code,
            stage_code=row.stage.code,
        )
        for row in rows
    ]


@router.post(
    "/object-stages",
    response_model=ObjectStageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_object_stage(
    request: Request,
    data: ObjectStageRequest,
    session: AsyncSession = Depends(get_session),
) -> ObjectStageResponse:
    _require_manager(_extract_user(request))
    existing = await session.execute(
        select(ObjectStage).where(
            ObjectStage.object_id == data.object_id,
            ObjectStage.stage_id == data.stage_id,
        )
    )
    link = existing.scalar_one_or_none()
    if link is not None:
        link.active = data.active
        await session.commit()
        await session.refresh(link)
    else:
        link = ObjectStage(
            object_id=data.object_id,
            stage_id=data.stage_id,
            active=data.active,
        )
        session.add(link)
        await session.commit()
        await session.refresh(link)
    obj = await session.get(Object, link.object_id)
    stage = await session.get(Stage, link.stage_id)
    return ObjectStageResponse(
        id=link.id,
        object_id=link.object_id,
        stage_id=link.stage_id,
        active=link.active,
        object_code=obj.code if obj else "",
        stage_code=stage.code if stage else "",
    )


@router.delete("/object-stages/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_object_stage(
    link_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> None:
    _require_manager(_extract_user(request))
    link = await session.get(ObjectStage, link_id)
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="link not found",
        )
    link.active = False
    await session.commit()


@router.get("/work-type-methods", response_model=list[WorkTypeMethodResponse])
async def list_work_type_methods(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> list[WorkTypeMethodResponse]:
    _require_manager(_extract_user(request))
    result = await session.execute(
        select(WorkTypeMethod)
        .join(WorkType)
        .join(WorkMethod)
        .order_by(WorkType.code, WorkMethod.name)
        .options(
            selectinload(WorkTypeMethod.work_type),
            selectinload(WorkTypeMethod.work_method),
        )
    )
    rows = result.scalars().all()
    return [
        WorkTypeMethodResponse(
            id=row.id,
            work_type_id=row.work_type_id,
            work_method_id=row.work_method_id,
            active=row.active,
            work_type_code=row.work_type.code,
            work_method_code=row.work_method.code,
        )
        for row in rows
    ]


@router.post(
    "/work-type-methods",
    response_model=WorkTypeMethodResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_work_type_method(
    request: Request,
    data: WorkTypeMethodRequest,
    session: AsyncSession = Depends(get_session),
) -> WorkTypeMethodResponse:
    _require_manager(_extract_user(request))
    existing = await session.execute(
        select(WorkTypeMethod).where(
            WorkTypeMethod.work_type_id == data.work_type_id,
            WorkTypeMethod.work_method_id == data.work_method_id,
        )
    )
    link = existing.scalar_one_or_none()
    if link is not None:
        link.active = data.active
        await session.commit()
        await session.refresh(link)
    else:
        link = WorkTypeMethod(
            work_type_id=data.work_type_id,
            work_method_id=data.work_method_id,
            active=data.active,
        )
        session.add(link)
        await session.commit()
        await session.refresh(link)
    wt = await session.get(WorkType, link.work_type_id)
    method = await session.get(WorkMethod, link.work_method_id)
    return WorkTypeMethodResponse(
        id=link.id,
        work_type_id=link.work_type_id,
        work_method_id=link.work_method_id,
        active=link.active,
        work_type_code=wt.code if wt else "",
        work_method_code=method.code if method else "",
    )


@router.delete("/work-type-methods/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_work_type_method(
    link_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> None:
    _require_manager(_extract_user(request))
    link = await session.get(WorkTypeMethod, link_id)
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="link not found",
        )
    link.active = False
    await session.commit()


@router.get("/assignments", response_model=list[AssignmentResponse])
async def list_assignments(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> list[AssignmentResponse]:
    _require_manager(_extract_user(request))
    result = await session.execute(
        select(ResponsibleObjectAssignment)
        .join(User)
        .join(Object)
        .order_by(User.full_name, Object.code)
        .options(
            selectinload(ResponsibleObjectAssignment.user),
            selectinload(ResponsibleObjectAssignment.object),
        )
    )
    rows = result.scalars().all()
    return [
        AssignmentResponse(
            id=row.id,
            user_id=row.user_id,
            object_id=row.object_id,
            active_from=row.active_from,
            active_to=row.active_to,
            schedule_type=row.schedule_type,
            active=row.active,
            user_name=row.user.full_name,
            object_code=row.object.code,
        )
        for row in rows
    ]


@router.post(
    "/assignments",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_assignment(
    request: Request,
    data: AssignmentRequest,
    session: AsyncSession = Depends(get_session),
) -> AssignmentResponse:
    _require_manager(_extract_user(request))
    existing = await session.execute(
        select(ResponsibleObjectAssignment).where(
            ResponsibleObjectAssignment.user_id == data.user_id,
            ResponsibleObjectAssignment.object_id == data.object_id,
        )
    )
    assignment = existing.scalar_one_or_none()
    if assignment is not None:
        assignment.active_from = data.active_from
        assignment.active_to = data.active_to
        assignment.schedule_type = data.schedule_type
        assignment.active = data.active
    else:
        assignment = ResponsibleObjectAssignment(
            user_id=data.user_id,
            object_id=data.object_id,
            active_from=data.active_from,
            active_to=data.active_to,
            schedule_type=data.schedule_type,
            active=data.active,
        )
        session.add(assignment)
    await session.commit()
    await session.refresh(assignment)
    user = await session.get(User, assignment.user_id)
    obj = await session.get(Object, assignment.object_id)
    return AssignmentResponse(
        id=assignment.id,
        user_id=assignment.user_id,
        object_id=assignment.object_id,
        active_from=assignment.active_from,
        active_to=assignment.active_to,
        schedule_type=assignment.schedule_type,
        active=assignment.active,
        user_name=user.full_name if user else "",
        object_code=obj.code if obj else "",
    )


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(
    assignment_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> None:
    _require_manager(_extract_user(request))
    assignment = await session.get(ResponsibleObjectAssignment, assignment_id)
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="assignment not found",
        )
    assignment.active = False
    await session.commit()


@router.get("/users", response_model=list[UserAdminResponse])
async def list_users(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> list[UserAdminResponse]:
    _require_manager(_extract_user(request))
    result = await session.execute(
        select(User).order_by(User.full_name)
    )
    return [UserAdminResponse.model_validate(u) for u in result.scalars().all()]


@router.post("/users", response_model=UserAdminResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: Request,
    data: UserAdminRequest,
    session: AsyncSession = Depends(get_session),
) -> UserAdminResponse:
    _require_manager(_extract_user(request))
    existing = await session.execute(select(User).where(User.max_user_id == data.max_user_id))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="user max_user_id already exists",
        )
    user = User(
        max_user_id=data.max_user_id,
        full_name=data.full_name,
        role=data.role,
        active=data.active,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return UserAdminResponse.model_validate(user)


@router.put("/users/{user_id}", response_model=UserAdminResponse)
async def update_user(
    user_id: int,
    request: Request,
    data: UserAdminRequest,
    session: AsyncSession = Depends(get_session),
) -> UserAdminResponse:
    _require_manager(_extract_user(request))
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user not found",
        )
    if data.max_user_id != user.max_user_id:
        existing = await session.execute(
            select(User).where(
                User.max_user_id == data.max_user_id, User.id != user_id
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="user max_user_id already exists",
            )
    user.max_user_id = data.max_user_id
    user.full_name = data.full_name
    user.role = data.role
    user.active = data.active
    await session.commit()
    await session.refresh(user)
    return UserAdminResponse.model_validate(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> None:
    _require_manager(_extract_user(request))
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user not found",
        )
    user.active = False
    await session.commit()
