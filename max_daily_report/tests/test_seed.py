from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.catalogs import ObjectStage, WorkTypeMethod
from app.models.users import GroupMember
from app.seed import seed_sync


def test_seed_is_idempotent(db_session: Session) -> None:
    seed_sync(db_session)
    first_object_stage_count = db_session.execute(
        select(func.count()).select_from(ObjectStage)
    ).scalar()
    first_member_count = db_session.execute(
        select(func.count()).select_from(GroupMember)
    ).scalar()
    first_wtm_count = db_session.execute(
        select(func.count()).select_from(WorkTypeMethod)
    ).scalar()

    seed_sync(db_session)

    assert db_session.execute(
        select(func.count()).select_from(ObjectStage)
    ).scalar() == first_object_stage_count
    assert db_session.execute(
        select(func.count()).select_from(GroupMember)
    ).scalar() == first_member_count
    assert db_session.execute(
        select(func.count()).select_from(WorkTypeMethod)
    ).scalar() == first_wtm_count

    # Spot check object-stage links are valid FKs.
    link = db_session.execute(select(ObjectStage).limit(1)).scalar_one_or_none()
    assert link is not None
    assert link.object_id is not None
    assert link.stage_id is not None
