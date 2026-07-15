from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.reports import ReportCreateRequest, StaffInput


def test_comment_max_length():
    data = ReportCreateRequest(
        report_date=date(2026, 7, 15),
        object_id=1,
        stage_id=1,
        staff=StaffInput(itr=1),
        comment="x" * 1000,
    )
    assert data.comment is not None
    assert len(data.comment) == 1000


def test_comment_too_long():
    with pytest.raises(ValidationError):
        ReportCreateRequest(
            report_date=date(2026, 7, 15),
            object_id=1,
            stage_id=1,
            staff=StaffInput(itr=1),
            comment="x" * 1001,
        )


def test_comment_optional():
    data = ReportCreateRequest(
        report_date=date(2026, 7, 15),
        object_id=1,
        stage_id=1,
        staff=StaffInput(itr=1),
    )
    assert data.comment is None
