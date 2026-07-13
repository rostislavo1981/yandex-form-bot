from __future__ import annotations

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

DEFAULT_LIMIT = 20
MAX_LIMIT = 50


def _normalize_query(q: str | None) -> str | None:
    if q is None:
        return None
    cleaned = q.strip().lower()
    return cleaned if cleaned else None


def _paginate(query, limit: int, offset: int):
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)
    return query.limit(limit).offset(offset)


def _catalog_search_filter(model, q: str | None):
    active_filter = model.active == True  # noqa: E712
    if q is None:
        return active_filter
    pattern = f"%{q}%"
    return active_filter & (
        func.lower(model.name).like(pattern)
        | func.lower(model.code).like(pattern)
        | func.lower(func.coalesce(model.search_aliases, "")).like(pattern)
    )


class CatalogService:
    """Business layer for catalog search."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search_objects(
        self, q: str | None, limit: int = DEFAULT_LIMIT, offset: int = 0
    ) -> tuple[list[Object], int]:
        q = _normalize_query(q)
        stmt = (
            select(Object)
            .where(_catalog_search_filter(Object, q))
            .order_by(Object.sort_order, Object.name)
        )
        total_result = await self._session.execute(
            select(func.count()).select_from(Object).where(_catalog_search_filter(Object, q))
        )
        total = total_result.scalar() or 0
        result = await self._session.execute(_paginate(stmt, limit, offset))
        return list(result.scalars().all()), total

    async def search_stages_for_object(
        self,
        object_id: int,
        q: str | None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> tuple[list[Stage], int]:
        q = _normalize_query(q)
        base_stmt = (
            select(Stage)
            .join(ObjectStage, ObjectStage.stage_id == Stage.id)
            .where(
                ObjectStage.object_id == object_id,
                ObjectStage.active == True,  # noqa: E712
                Stage.active == True,  # noqa: E712
            )
        )
        if q is not None:
            pattern = f"%{q}%"
            base_stmt = base_stmt.where(
                func.lower(Stage.name).like(pattern)
                | func.lower(Stage.code).like(pattern)
                | func.lower(func.coalesce(Stage.search_aliases, "")).like(pattern)
            )
        stmt = base_stmt.order_by(Stage.sort_order, Stage.name)
        total_result = await self._session.execute(
            select(func.count()).select_from(base_stmt.subquery())
        )
        total = total_result.scalar() or 0
        result = await self._session.execute(_paginate(stmt, limit, offset))
        return list(result.scalars().all()), total

    async def search_equipment(
        self, q: str | None, limit: int = DEFAULT_LIMIT, offset: int = 0
    ) -> tuple[list[EquipmentType], int]:
        q = _normalize_query(q)
        stmt = (
            select(EquipmentType)
            .where(_catalog_search_filter(EquipmentType, q))
            .order_by(EquipmentType.sort_order, EquipmentType.name)
        )
        total_result = await self._session.execute(
            select(func.count())
            .select_from(EquipmentType)
            .where(_catalog_search_filter(EquipmentType, q))
        )
        total = total_result.scalar() or 0
        result = await self._session.execute(_paginate(stmt, limit, offset))
        return list(result.scalars().all()), total

    async def search_work_types(
        self,
        q: str | None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> tuple[list[WorkType], int]:
        q = _normalize_query(q)
        stmt = (
            select(WorkType)
            .where(_catalog_search_filter(WorkType, q))
            .order_by(WorkType.sort_order, WorkType.name)
        )
        total_result = await self._session.execute(
            select(func.count())
            .select_from(WorkType)
            .where(_catalog_search_filter(WorkType, q))
        )
        total = total_result.scalar() or 0
        result = await self._session.execute(_paginate(stmt, limit, offset))
        return list(result.scalars().all()), total

    async def search_work_methods_for_type(
        self,
        work_type_id: int,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> tuple[list[WorkMethod], int]:
        stmt = (
            select(WorkMethod)
            .join(WorkTypeMethod, WorkTypeMethod.work_method_id == WorkMethod.id)
            .where(
                WorkTypeMethod.work_type_id == work_type_id,
                WorkTypeMethod.active == True,  # noqa: E712
                WorkMethod.active == True,  # noqa: E712
            )
            .order_by(WorkMethod.sort_order, WorkMethod.name)
        )
        total_result = await self._session.execute(
            select(func.count()).select_from(stmt.subquery())
        )
        total = total_result.scalar() or 0
        result = await self._session.execute(_paginate(stmt, limit, offset))
        return list(result.scalars().all()), total

    async def list_units(
        self,
        q: str | None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> tuple[list[Unit], int]:
        q = _normalize_query(q)
        stmt = (
            select(Unit)
            .where(_catalog_search_filter(Unit, q))
            .order_by(Unit.sort_order, Unit.name)
        )
        total_result = await self._session.execute(
            select(func.count()).select_from(Unit).where(_catalog_search_filter(Unit, q))
        )
        total = total_result.scalar() or 0
        result = await self._session.execute(_paginate(stmt, limit, offset))
        return list(result.scalars().all()), total
