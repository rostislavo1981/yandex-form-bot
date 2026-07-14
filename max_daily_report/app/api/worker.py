from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session, require_internal
from app.services.notification_worker import NotificationWorker

router = APIRouter(
    prefix="/api/worker",
    tags=["worker"],
    dependencies=[Depends(require_internal)],
)


@router.post("/process-outbox")
async def process_outbox(
    session: AsyncSession = Depends(get_session),
    limit: int = 50,
) -> dict[str, int]:
    worker = NotificationWorker(session)
    return await worker.process_pending(limit=limit)
