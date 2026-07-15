from __future__ import annotations

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
from app.models.users import MAXGroup, User


class CatalogRepo:
    """Read/write helpers for catalog seeding."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create_user(
        self,
        max_user_id: str,
        full_name: str,
        role: str,
    ) -> User:
        result = await self._session.execute(
            select(User).where(User.max_user_id == max_user_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(max_user_id=max_user_id, full_name=full_name, role=role)
            self._session.add(user)
        else:
            user.full_name = full_name
            user.role = role
            user.active = True
        await self._session.flush()
        return user

    async def get_or_create_group(self, chat_id: str, title: str) -> MAXGroup:
        result = await self._session.execute(
            select(MAXGroup).where(MAXGroup.chat_id == chat_id)
        )
        group = result.scalar_one_or_none()
        if group is None:
            group = MAXGroup(chat_id=chat_id, title=title)
            self._session.add(group)
        else:
            group.title = title
            group.active = True
        await self._session.flush()
        return group

    async def get_or_create_contractor(self, code: str, name: str) -> Contractor:
        result = await self._session.execute(
            select(Contractor).where(Contractor.code == code)
        )
        contractor = result.scalar_one_or_none()
        if contractor is None:
            contractor = Contractor(code=code, name=name)
            self._session.add(contractor)
        else:
            contractor.name = name
            contractor.active = True
        await self._session.flush()
        return contractor

    async def get_or_create_unit(self, code: str, name: str, symbol: str) -> Unit:
        result = await self._session.execute(select(Unit).where(Unit.code == code))
        unit = result.scalar_one_or_none()
        if unit is None:
            unit = Unit(code=code, name=name, symbol=symbol)
            self._session.add(unit)
        else:
            unit.name = name
            unit.symbol = symbol
            unit.active = True
        await self._session.flush()
        return unit

    async def get_or_create_stage(self, code: str, name: str) -> Stage:
        result = await self._session.execute(select(Stage).where(Stage.code == code))
        stage = result.scalar_one_or_none()
        if stage is None:
            stage = Stage(code=code, name=name)
            self._session.add(stage)
        else:
            stage.name = name
            stage.active = True
        await self._session.flush()
        return stage

    async def get_or_create_object(
        self,
        code: str,
        name: str,
        execution_method: str | None = None,
        default_contractor_id: int | None = None,
    ) -> Object:
        result = await self._session.execute(
            select(Object).where(Object.code == code)
        )
        obj = result.scalar_one_or_none()
        if obj is None:
            obj = Object(
                code=code,
                name=name,
                execution_method=execution_method,
                default_contractor_id=default_contractor_id,
            )
            self._session.add(obj)
        else:
            obj.name = name
            obj.execution_method = execution_method
            obj.default_contractor_id = default_contractor_id
            obj.active = True
        await self._session.flush()
        return obj

    async def ensure_object_stage(self, object_id: int, stage_id: int) -> None:
        result = await self._session.execute(
            select(ObjectStage).where(
                ObjectStage.object_id == object_id,
                ObjectStage.stage_id == stage_id,
            )
        )
        link = result.scalar_one_or_none()
        if link is None:
            self._session.add(ObjectStage(object_id=object_id, stage_id=stage_id))
        else:
            link.active = True
        await self._session.flush()

    async def get_or_create_equipment_type(
        self,
        code: str,
        name: str,
        default_unit_id: int | None = None,
    ) -> EquipmentType:
        result = await self._session.execute(
            select(EquipmentType).where(EquipmentType.code == code)
        )
        equipment = result.scalar_one_or_none()
        if equipment is None:
            equipment = EquipmentType(
                code=code, name=name, default_unit_id=default_unit_id
            )
            self._session.add(equipment)
        else:
            equipment.name = name
            equipment.default_unit_id = default_unit_id
            equipment.active = True
        await self._session.flush()
        return equipment

    async def get_or_create_work_type(
        self,
        code: str,
        name: str,
        default_unit_id: int | None = None,
    ) -> WorkType:
        result = await self._session.execute(
            select(WorkType).where(WorkType.code == code)
        )
        work_type = result.scalar_one_or_none()
        if work_type is None:
            work_type = WorkType(
                code=code, name=name, default_unit_id=default_unit_id
            )
            self._session.add(work_type)
        else:
            work_type.name = name
            work_type.default_unit_id = default_unit_id
            work_type.active = True
        await self._session.flush()
        return work_type

    async def get_or_create_work_method(self, code: str, name: str) -> WorkMethod:
        result = await self._session.execute(
            select(WorkMethod).where(WorkMethod.code == code)
        )
        method = result.scalar_one_or_none()
        if method is None:
            method = WorkMethod(code=code, name=name)
            self._session.add(method)
        else:
            method.name = name
            method.active = True
        await self._session.flush()
        return method

    async def ensure_work_type_method(
        self, work_type_id: int, work_method_id: int
    ) -> None:
        result = await self._session.execute(
            select(WorkTypeMethod).where(
                WorkTypeMethod.work_type_id == work_type_id,
                WorkTypeMethod.work_method_id == work_method_id,
            )
        )
        link = result.scalar_one_or_none()
        if link is None:
            self._session.add(
                WorkTypeMethod(work_type_id=work_type_id, work_method_id=work_method_id)
            )
        else:
            link.active = True
        await self._session.flush()
