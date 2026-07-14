from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reports import ReportObligation, ResponsibleObjectAssignment


def _is_workday(target_date: date) -> bool:
    return target_date.weekday() < 5


def _due_at_for_date(target_date: date, tz_name: str = "Europe/Moscow") -> datetime:
    return datetime.combine(target_date, time(23, 59, 59))


class ObligationService:
    """Generate or refresh report obligations for assignments and date range."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def generate_for_date_range(
        self,
        start_date: date,
        end_date: date,
    ) -> tuple[int, int]:
        """Generate obligations for all active assignments in the date range.

        Returns (created, skipped).
        """
        result = await self._session.execute(
            select(ResponsibleObjectAssignment).where(
                ResponsibleObjectAssignment.active.is_(True)
            )
        )
        assignments: Sequence[ResponsibleObjectAssignment] = result.scalars().all()

        created = 0
        skipped = 0
        for assignment in assignments:
            for current in self._date_range(start_date, end_date):
                if assignment.schedule_type == "weekdays" and not _is_workday(current):
                    skipped += 1
                    continue
                obligation = await self._ensure_obligation(assignment, current)
                if obligation._created_in_this_call:
                    created += 1
                else:
                    skipped += 1
        await self._session.commit()
        return created, skipped

    async def _ensure_obligation(
        self,
        assignment: ResponsibleObjectAssignment,
        target_date: date,
    ) -> ReportObligation:
        result = await self._session.execute(
            select(ReportObligation).where(
                ReportObligation.report_date == target_date,
                ReportObligation.assignment_id == assignment.id,
            )
        )
        obligation = result.scalar_one_or_none()
        if obligation is None:
            obligation = ReportObligation(
                report_date=target_date,
                assignment_id=assignment.id,
                user_id=assignment.user_id,
                object_id=assignment.object_id,
                status="pending",
                due_at=_due_at_for_date(target_date),
            )
            self._session.add(obligation)
            obligation._created_in_this_call = True
        else:
            obligation._created_in_this_call = False
        return obligation

    @staticmethod
    def _date_range(start_date: date, end_date: date):
        current = start_date
        while current <= end_date:
            yield current
            current += timedelta(days=1)


async def generate_obligations(
    session: AsyncSession,
    start_date: date,
    end_date: date,
) -> tuple[int, int]:
    service = ObligationService(session)
    return await service.generate_for_date_range(start_date, end_date)
