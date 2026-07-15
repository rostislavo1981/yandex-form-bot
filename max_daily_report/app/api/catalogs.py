from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session, require_user
from app.models.users import User
from app.schemas.catalogs import (
    CatalogItem,
    CatalogItemWithSymbol,
    CatalogListResponse,
    UnitListResponse,
)
from app.services.catalog_service import CatalogService

router = APIRouter(
    prefix="/api/catalogs", tags=["catalogs"], dependencies=[Depends(require_user)]
)


def _pagination(
    q: str | None = Query(None, description="Поиск по названию, коду или псевдонимам"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
) -> dict:
    return {"q": q, "limit": limit, "offset": offset}


@router.get("/objects", response_model=CatalogListResponse)
async def search_objects(
    pagination: dict = Depends(_pagination),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_user),
) -> CatalogListResponse:
    service = CatalogService(session)
    restrict_user_id = user.id if user.role == "responsible" else None
    items, total = await service.search_objects(
        q=pagination["q"],
        limit=pagination["limit"],
        offset=pagination["offset"],
        restrict_user_id=restrict_user_id,
    )
    return CatalogListResponse(
        items=[CatalogItem.model_validate(obj) for obj in items], total=total
    )


@router.get("/objects/{object_id}/stages", response_model=CatalogListResponse)
async def search_object_stages(
    object_id: int,
    pagination: dict = Depends(_pagination),
    session: AsyncSession = Depends(get_session),
) -> CatalogListResponse:
    service = CatalogService(session)
    items, total = await service.search_stages_for_object(
        object_id=object_id,
        q=pagination["q"],
        limit=pagination["limit"],
        offset=pagination["offset"],
    )
    return CatalogListResponse(
        items=[CatalogItem.model_validate(stage) for stage in items], total=total
    )


@router.get("/equipment", response_model=CatalogListResponse)
async def search_equipment(
    pagination: dict = Depends(_pagination),
    session: AsyncSession = Depends(get_session),
) -> CatalogListResponse:
    service = CatalogService(session)
    items, total = await service.search_equipment(
        q=pagination["q"], limit=pagination["limit"], offset=pagination["offset"]
    )
    return CatalogListResponse(
        items=[CatalogItem.model_validate(item) for item in items], total=total
    )


@router.get("/work-types", response_model=CatalogListResponse)
async def search_work_types(
    pagination: dict = Depends(_pagination),
    session: AsyncSession = Depends(get_session),
) -> CatalogListResponse:
    service = CatalogService(session)
    items, total = await service.search_work_types(
        q=pagination["q"], limit=pagination["limit"], offset=pagination["offset"]
    )
    return CatalogListResponse(
        items=[CatalogItem.model_validate(item) for item in items], total=total
    )


@router.get("/work-types/{work_type_id}/methods", response_model=CatalogListResponse)
async def search_work_type_methods(
    work_type_id: int,
    pagination: dict = Depends(_pagination),
    session: AsyncSession = Depends(get_session),
) -> CatalogListResponse:
    service = CatalogService(session)
    items, total = await service.search_work_methods_for_type(
        work_type_id=work_type_id,
        limit=pagination["limit"],
        offset=pagination["offset"],
    )
    return CatalogListResponse(
        items=[CatalogItem.model_validate(item) for item in items], total=total
    )


@router.get("/units", response_model=UnitListResponse)
async def list_units(
    pagination: dict = Depends(_pagination),
    session: AsyncSession = Depends(get_session),
) -> UnitListResponse:
    service = CatalogService(session)
    items, total = await service.list_units(
        q=pagination["q"], limit=pagination["limit"], offset=pagination["offset"]
    )
    return UnitListResponse(
        items=[CatalogItemWithSymbol.model_validate(item) for item in items], total=total
    )


@router.get("/contractors", response_model=CatalogListResponse)
async def search_contractors(
    pagination: dict = Depends(_pagination),
    session: AsyncSession = Depends(get_session),
) -> CatalogListResponse:
    service = CatalogService(session)
    items, total = await service.search_contractors(
        q=pagination["q"], limit=pagination["limit"], offset=pagination["offset"]
    )
    return CatalogListResponse(
        items=[CatalogItem.model_validate(item) for item in items], total=total
    )
