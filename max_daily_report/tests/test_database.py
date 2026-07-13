from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import (
    Contractor,
    EquipmentType,
    MAXGroup,
    Object,
    ObjectStage,
    Stage,
    Unit,
    User,
    WorkMethod,
    WorkType,
    WorkTypeMethod,
)


def test_tables_exist_and_fixture_is_clean(db_session: Session) -> None:
    suffix = uuid.uuid4().hex[:8]
    contractor = Contractor(code=f"c-{suffix}", name="Подрядчик")
    unit = Unit(code=f"m3-{suffix}", name="кубометр", symbol="м³")
    db_session.add_all([contractor, unit])
    db_session.flush()

    obj = Object(
        code=f"obj-{suffix}",
        name="Объект 1",
        execution_method="own",
        default_contractor_id=contractor.id,
    )
    stage = Stage(code=f"st-{suffix}", name="Этап 1")
    user = User(max_user_id=f"max-{suffix}", full_name="Иван", role="responsible")
    group = MAXGroup(chat_id=f"g-{suffix}", title="Группа")
    db_session.add_all([obj, stage, user, group])
    db_session.flush()

    object_stage = ObjectStage(object_id=obj.id, stage_id=stage.id)
    equipment_type = EquipmentType(
        code=f"exc-{suffix}", name="Экскаватор", default_unit_id=unit.id
    )
    work_type = WorkType(
        code=f"dig-{suffix}", name="Земляные работы", default_unit_id=unit.id
    )
    work_method = WorkMethod(code=f"manual-{suffix}", name="Вручную")
    db_session.add_all([object_stage, equipment_type, work_type, work_method])
    db_session.flush()

    work_type_method = WorkTypeMethod(
        work_type_id=work_type.id,
        work_method_id=work_method.id,
    )
    db_session.add(work_type_method)
    db_session.commit()

    result = db_session.execute(text("SELECT count(*) FROM users"))
    assert result.scalar() == 1

    found = db_session.get(User, user.id)
    assert found is not None
    assert found.role == "responsible"
