from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import engine
from app.models.catalogs import (
    Contractor,
    EquipmentType,
    Object,
    ObjectStage,
    Stage,
    Unit,
    WorkMethod,
    WorkType,
)
from app.models.reports import ResponsibleObjectAssignment
from app.models.users import GroupMember, MAXGroup, User
from app.repos.catalogs import CatalogRepo

logger = logging.getLogger(__name__)

SEED_USERS = [
    {"max_user_id": "max-manager-1", "full_name": "Петров М.И.", "role": "manager"},
    {"max_user_id": "max-resp-1", "full_name": "Иванов А.В.", "role": "responsible"},
    {"max_user_id": "max-resp-2", "full_name": "Сидоров К.П.", "role": "responsible"},
    {"max_user_id": "dev-user", "full_name": "Dev User", "role": "admin"},
]

SEED_GROUP = {"chat_id": "max-group-1", "title": "Строительный участок №1"}

SEED_CONTRACTORS = [
    {"code": "own", "name": "Собственные силы"},
    {"code": "spetstroy", "name": "ООО СпецСтрой"},
]

SEED_UNITS = [
    {"code": "m3", "name": "кубометр", "symbol": "м³"},
    {"code": "m2", "name": "квадратный метр", "symbol": "м²"},
    {"code": "ton", "name": "тонна", "symbol": "т"},
    {"code": "pcs", "name": "штука", "symbol": "шт"},
    {"code": "hm", "name": "час-машина", "symbol": "ч/м"},
    {"code": "km", "name": "километр", "symbol": "км"},
]

SEED_STAGES = [
    {"code": "prep", "name": "Подготовительные работы"},
    {"code": "zero", "name": "Нулевой цикл"},
    {"code": "frame", "name": "Каркас"},
    {"code": "facade", "name": "Фасад"},
]

SEED_OBJECTS = [
    {
        "code": "obj-1",
        "name": "ЖК Северный объект 1",
        "execution_method": "own",
        "default_contractor_code": "own",
        "stage_codes": ["prep", "zero"],
    },
    {
        "code": "obj-2",
        "name": "ЖК Северный объект 2",
        "execution_method": "contractor",
        "default_contractor_code": "spetstroy",
        "stage_codes": ["zero", "frame"],
    },
]

SEED_EQUIPMENT = [
    {"code": "exc-200", "name": "Экскаватор 200", "default_unit_code": "hm"},
    {"code": "dump-20", "name": "Самосвал 20т", "default_unit_code": "hm"},
    {"code": "bulldozer", "name": "Бульдозер", "default_unit_code": "hm"},
]

SEED_WORK_TYPES = [
    {
        "code": "dig",
        "name": "Земляные работы",
        "default_unit_code": "m3",
        "method_codes": ["manual", "machine"],
    },
    {
        "code": "concrete",
        "name": "Бетонные работы",
        "default_unit_code": "m3",
        "method_codes": ["machine"],
    },
    {
        "code": "formwork",
        "name": "Опалубка",
        "default_unit_code": "m2",
        "method_codes": ["manual"],
    },
]

SEED_WORK_METHODS = [
    {"code": "manual", "name": "Вручную"},
    {"code": "machine", "name": "Механизированно"},
]

SEED_ASSIGNMENTS = [
    {"max_user_id": "max-resp-1", "object_code": "obj-1", "schedule_type": "daily"},
    {"max_user_id": "max-resp-2", "object_code": "obj-2", "schedule_type": "daily"},
]


async def seed_async(session: AsyncSession) -> None:
    """Idempotently seed minimal catalog data (async)."""
    repo = CatalogRepo(session)

    users: list[User] = []
    for item in SEED_USERS:
        user = await repo.get_or_create_user(
            max_user_id=item["max_user_id"],
            full_name=item["full_name"],
            role=item["role"],
        )
        users.append(user)

    group_chat_id = settings.max_group_id.strip() or SEED_GROUP["chat_id"]
    group = await repo.get_or_create_group(
        chat_id=group_chat_id,
        title=SEED_GROUP["title"],
    )
    if settings.max_group_id:
        await session.execute(
            update(MAXGroup)
            .where(MAXGroup.chat_id == SEED_GROUP["chat_id"])
            .where(MAXGroup.chat_id != group_chat_id)
            .values(active=False)
        )

    for user in users:
        result = await session.execute(
            select(GroupMember).where(
                GroupMember.group_id == group.id,
                GroupMember.user_id == user.id,
            )
        )
        member = result.scalar_one_or_none()
        if member is None:
            session.add(
                GroupMember(group_id=group.id, user_id=user.id, active=True)
            )
        else:
            member.active = True
    await session.flush()

    contractors: dict[str, Contractor] = {}
    for item in SEED_CONTRACTORS:
        contractors[item["code"]] = await repo.get_or_create_contractor(
            code=item["code"], name=item["name"]
        )

    units: dict[str, Unit] = {}
    for item in SEED_UNITS:
        units[item["code"]] = await repo.get_or_create_unit(
            code=item["code"], name=item["name"], symbol=item["symbol"]
        )

    stages: dict[str, Stage] = {}
    for item in SEED_STAGES:
        stages[item["code"]] = await repo.get_or_create_stage(
            code=item["code"], name=item["name"]
        )

    methods: dict[str, WorkMethod] = {}
    for item in SEED_WORK_METHODS:
        methods[item["code"]] = await repo.get_or_create_work_method(
            code=item["code"], name=item["name"]
        )

    objects: list[Object] = []
    for item in SEED_OBJECTS:
        obj = await repo.get_or_create_object(
            code=item["code"],
            name=item["name"],
            execution_method=item.get("execution_method"),
            default_contractor_id=contractors.get(
                item.get("default_contractor_code") or ""
            ).id
            if item.get("default_contractor_code")
            else None,
        )
        objects.append(obj)
        for stage_code in item.get("stage_codes", []):
            await repo.ensure_object_stage(obj.id, stages[stage_code].id)

    for item in SEED_EQUIPMENT:
        await repo.get_or_create_equipment_type(
            code=item["code"],
            name=item["name"],
            default_unit_id=units[item["default_unit_code"]].id,
        )

    for item in SEED_WORK_TYPES:
        work_type = await repo.get_or_create_work_type(
            code=item["code"],
            name=item["name"],
            default_unit_id=units[item["default_unit_code"]].id,
        )
        for method_code in item.get("method_codes", []):
            await repo.ensure_work_type_method(work_type.id, methods[method_code].id)

    for item in SEED_ASSIGNMENTS:
        user = next((u for u in users if u.max_user_id == item["max_user_id"]), None)
        obj = next((o for o in objects if o.code == item["object_code"]), None)
        if user is None or obj is None:
            continue
        result = await session.execute(
            select(ResponsibleObjectAssignment).where(
                ResponsibleObjectAssignment.user_id == user.id,
                ResponsibleObjectAssignment.object_id == obj.id,
            )
        )
        assignment = result.scalar_one_or_none()
        if assignment is None:
            from datetime import date

            session.add(
                ResponsibleObjectAssignment(
                    user_id=user.id,
                    object_id=obj.id,
                    active_from=date(2024, 1, 1),
                    active_to=date(2030, 12, 31),
                    schedule_type=item["schedule_type"],
                    active=True,
                )
            )
        else:
            assignment.active = True
            assignment.schedule_type = item["schedule_type"]
    await session.flush()

    await session.commit()
    logger.info("Seed completed successfully")


def seed_sync(session: object) -> None:
    """Idempotently seed minimal catalog data (sync for tests)."""
    from sqlalchemy import select as sync_select

    def get_or_create_user(max_user_id: str, full_name: str, role: str) -> User:
        user = session.execute(
            sync_select(User).where(User.max_user_id == max_user_id)
        ).scalar_one_or_none()
        if user is None:
            user = User(max_user_id=max_user_id, full_name=full_name, role=role)
            session.add(user)
        else:
            user.full_name = full_name
            user.role = role
            user.active = True
        session.flush()
        return user

    def get_or_create_group(chat_id: str, title: str) -> MAXGroup:
        group = session.execute(
            sync_select(MAXGroup).where(MAXGroup.chat_id == chat_id)
        ).scalar_one_or_none()
        if group is None:
            group = MAXGroup(chat_id=chat_id, title=title)
            session.add(group)
        else:
            group.title = title
            group.active = True
        session.flush()
        return group

    def get_or_create_contractor(code: str, name: str) -> Contractor:
        contractor = session.execute(
            sync_select(Contractor).where(Contractor.code == code)
        ).scalar_one_or_none()
        if contractor is None:
            contractor = Contractor(code=code, name=name)
            session.add(contractor)
        else:
            contractor.name = name
            contractor.active = True
        session.flush()
        return contractor

    def get_or_create_unit(code: str, name: str, symbol: str) -> Unit:
        unit = session.execute(
            sync_select(Unit).where(Unit.code == code)
        ).scalar_one_or_none()
        if unit is None:
            unit = Unit(code=code, name=name, symbol=symbol)
            session.add(unit)
        else:
            unit.name = name
            unit.symbol = symbol
            unit.active = True
        session.flush()
        return unit

    def get_or_create_stage(code: str, name: str) -> Stage:
        stage = session.execute(
            sync_select(Stage).where(Stage.code == code)
        ).scalar_one_or_none()
        if stage is None:
            stage = Stage(code=code, name=name)
            session.add(stage)
        else:
            stage.name = name
            stage.active = True
        session.flush()
        return stage

    def get_or_create_equipment_type(
        code: str, name: str, default_unit_id: int
    ) -> EquipmentType:
        equipment = session.execute(
            sync_select(EquipmentType).where(EquipmentType.code == code)
        ).scalar_one_or_none()
        if equipment is None:
            equipment = EquipmentType(
                code=code, name=name, default_unit_id=default_unit_id
            )
            session.add(equipment)
        else:
            equipment.name = name
            equipment.default_unit_id = default_unit_id
            equipment.active = True
        session.flush()
        return equipment

    def get_or_create_work_type(
        code: str, name: str, default_unit_id: int
    ) -> WorkType:
        work_type = session.execute(
            sync_select(WorkType).where(WorkType.code == code)
        ).scalar_one_or_none()
        if work_type is None:
            work_type = WorkType(
                code=code, name=name, default_unit_id=default_unit_id
            )
            session.add(work_type)
        else:
            work_type.name = name
            work_type.default_unit_id = default_unit_id
            work_type.active = True
        session.flush()
        return work_type

    def get_or_create_work_method(code: str, name: str) -> WorkMethod:
        method = session.execute(
            sync_select(WorkMethod).where(WorkMethod.code == code)
        ).scalar_one_or_none()
        if method is None:
            method = WorkMethod(code=code, name=name)
            session.add(method)
        else:
            method.name = name
            method.active = True
        session.flush()
        return method

    def get_or_create_object(
        code: str,
        name: str,
        execution_method: str | None,
        default_contractor_id: int | None,
    ) -> Object:
        obj = session.execute(
            sync_select(Object).where(Object.code == code)
        ).scalar_one_or_none()
        if obj is None:
            obj = Object(
                code=code,
                name=name,
                execution_method=execution_method,
                default_contractor_id=default_contractor_id,
            )
            session.add(obj)
        else:
            obj.name = name
            obj.execution_method = execution_method
            obj.default_contractor_id = default_contractor_id
            obj.active = True
        session.flush()
        return obj

    def ensure_object_stage(object_id: int, stage_id: int) -> None:
        link = session.execute(
            sync_select(ObjectStage).where(
                ObjectStage.object_id == object_id,
                ObjectStage.stage_id == stage_id,
            )
        ).scalar_one_or_none()
        if link is None:
            session.add(ObjectStage(object_id=object_id, stage_id=stage_id))
        else:
            link.active = True
        session.flush()

    def ensure_work_type_method(work_type_id: int, work_method_id: int) -> None:
        from app.models.catalogs import WorkTypeMethod

        link = session.execute(
            sync_select(WorkTypeMethod).where(
                WorkTypeMethod.work_type_id == work_type_id,
                WorkTypeMethod.work_method_id == work_method_id,
            )
        ).scalar_one_or_none()
        if link is None:
            session.add(
                WorkTypeMethod(
                    work_type_id=work_type_id, work_method_id=work_method_id
                )
            )
        else:
            link.active = True
        session.flush()

    users = [
        get_or_create_user(u["max_user_id"], u["full_name"], u["role"])
        for u in SEED_USERS
    ]
    group_chat_id = settings.max_group_id.strip() or SEED_GROUP["chat_id"]
    group = get_or_create_group(group_chat_id, SEED_GROUP["title"])
    if settings.max_group_id:
        session.execute(
            update(MAXGroup)
            .where(MAXGroup.chat_id == SEED_GROUP["chat_id"])
            .where(MAXGroup.chat_id != group_chat_id)
            .values(active=False)
        )
    for user in users:
        member = session.execute(
            sync_select(GroupMember).where(
                GroupMember.group_id == group.id,
                GroupMember.user_id == user.id,
            )
        ).scalar_one_or_none()
        if member is None:
            session.add(
                GroupMember(group_id=group.id, user_id=user.id, active=True)
            )
        else:
            member.active = True
    session.flush()

    contractors = {
        item["code"]: get_or_create_contractor(item["code"], item["name"])
        for item in SEED_CONTRACTORS
    }
    units = {
        item["code"]: get_or_create_unit(item["code"], item["name"], item["symbol"])
        for item in SEED_UNITS
    }
    stages = {
        item["code"]: get_or_create_stage(item["code"], item["name"])
        for item in SEED_STAGES
    }
    methods = {
        item["code"]: get_or_create_work_method(item["code"], item["name"])
        for item in SEED_WORK_METHODS
    }

    for item in SEED_OBJECTS:
        obj = get_or_create_object(
            item["code"],
            item["name"],
            item.get("execution_method"),
            contractors[item["default_contractor_code"]].id
            if item.get("default_contractor_code")
            else None,
        )
        for stage_code in item.get("stage_codes", []):
            ensure_object_stage(obj.id, stages[stage_code].id)

    for item in SEED_EQUIPMENT:
        get_or_create_equipment_type(
            item["code"], item["name"], units[item["default_unit_code"]].id
        )

    for item in SEED_WORK_TYPES:
        work_type = get_or_create_work_type(
            item["code"], item["name"], units[item["default_unit_code"]].id
        )
        for method_code in item.get("method_codes", []):
            ensure_work_type_method(work_type.id, methods[method_code].id)

    object_map = {
        obj.code: obj
        for obj in [
            get_or_create_object(
                item["code"],
                item["name"],
                item.get("execution_method"),
                contractors[item["default_contractor_code"]].id
                if item.get("default_contractor_code")
                else None,
            )
            for item in SEED_OBJECTS
        ]
    }
    user_map = {user.max_user_id: user for user in users}
    for item in SEED_ASSIGNMENTS:
        user = user_map.get(item["max_user_id"])
        obj = object_map.get(item["object_code"])
        if user is None or obj is None:
            continue
        assignment = session.execute(
            sync_select(ResponsibleObjectAssignment).where(
                ResponsibleObjectAssignment.user_id == user.id,
                ResponsibleObjectAssignment.object_id == obj.id,
            )
        ).scalar_one_or_none()
        if assignment is None:
            from datetime import date

            session.add(
                ResponsibleObjectAssignment(
                    user_id=user.id,
                    object_id=obj.id,
                    active_from=date(2024, 1, 1),
                    active_to=date(2030, 12, 31),
                    schedule_type=item["schedule_type"],
                    active=True,
                )
            )
        else:
            assignment.active = True
            assignment.schedule_type = item["schedule_type"]
    session.flush()

    session.commit()
    logger.info("Seed completed successfully")


async def seed(session: AsyncSession) -> None:
    """Public async alias."""
    await seed_async(session)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        await seed(session)


if __name__ == "__main__":
    asyncio.run(main())
