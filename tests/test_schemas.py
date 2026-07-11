"""Tests for backend.schemas.Report."""
from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from backend.schemas import Material, Report, WorkItem


def test_minimal_report_valid() -> None:
    r = Report(
        date="2026-07-10",
        object_name="РП-7 Каменка",
        foreman="Степанов",
    )
    assert r.date == date(2026, 7, 10)
    assert r.object_name == "РП-7 Каменка"
    assert r.foreman == "Степанов"
    assert r.works == []
    assert r.materials == []
    assert r.notes is None


def test_date_accepts_datetime_string() -> None:
    r = Report(
        date="2026-07-10T15:30:00",
        object_name="X",
        foreman="Y",
    )
    assert r.date == date(2026, 7, 10)


def test_invalid_date_raises() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Report(date="not-a-date", object_name="X", foreman="Y")
    assert "date" in str(exc_info.value).lower()


def test_works_and_materials() -> None:
    r = Report(
        date="2026-07-10",
        object_name="X",
        foreman="Y",
        works=[
            WorkItem(name="копка", volume=50, unit="м", people_count=4),
            WorkItem(name="укладка", volume=50, unit="м"),
        ],
        materials=[Material(name="кабель", qty=200, unit="м")],
    )
    assert len(r.works) == 2
    assert r.works[0].people_count == 4
    assert r.works[1].people_count is None
    assert r.materials[0].qty == 200


def test_workitem_rejects_negative_volume() -> None:
    with pytest.raises(ValidationError):
        WorkItem(name="x", volume=-1, unit="м")


def test_workitem_rejects_blank_name_at_report_level() -> None:
    """WorkItem itself allows empty name (parser-tolerance),
    but Report filters them out via _strip_empties."""
    r = Report(
        date="2026-07-10",
        object_name="X",
        foreman="Y",
        works=[WorkItem(name="  ", volume=1, unit="м"), WorkItem(name="копка", volume=5, unit="м")],
    )
    assert len(r.works) == 1
    assert r.works[0].name == "копка"


def test_empty_works_get_dropped() -> None:
    r = Report(
        date="2026-07-10",
        object_name="X",
        foreman="Y",
        works=[WorkItem(name="", volume=1, unit="м"), WorkItem(name="копка", volume=5, unit="м")],
    )
    assert len(r.works) == 1
    assert r.works[0].name == "копка"


def test_to_form_payload_two_works() -> None:
    r = Report(
        date="2026-07-10",
        object_name="РП-7",
        foreman="Степанов",
        works=[
            WorkItem(name="копка", volume=50, unit="м", people_count=4),
            WorkItem(name="укладка", volume=50, unit="м"),
        ],
        notes="по плану",
    )
    p = r.to_form_payload()
    assert p["date"] == "2026-07-10"
    assert p["work_1_name"] == "копка"
    assert p["work_1_volume"] == 50
    assert p["work_1_people"] == 4
    assert p["work_2_name"] == "укладка"
    assert p["work_2_people"] is None
    assert p["notes"] == "по плану"


def test_to_form_payload_one_work_leaves_second_empty() -> None:
    r = Report(
        date="2026-07-10",
        object_name="X",
        foreman="Y",
        works=[WorkItem(name="копка", volume=10, unit="м")],
    )
    p = r.to_form_payload()
    assert p["work_1_name"] == "копка"
    assert p["work_2_name"] == ""
    assert p["work_2_volume"] == 0.0


def test_to_form_payload_three_works_pushes_extras_to_notes() -> None:
    r = Report(
        date="2026-07-10",
        object_name="X",
        foreman="Y",
        works=[
            WorkItem(name="копка", volume=10, unit="м"),
            WorkItem(name="укладка", volume=10, unit="м"),
            WorkItem(name="засыпка", volume=10, unit="м"),
        ],
        notes="ок",
    )
    p = r.to_form_payload()
    assert "доп. работы" in p["notes"]
    assert "засыпка 10 м" in p["notes"]


def test_extra_fields_ignored() -> None:
    """Forward-compat: YandexGPT may add new fields; we don't crash."""
    r = Report.model_validate(
        {
            "date": "2026-07-10",
            "object_name": "X",
            "foreman": "Y",
            "future_field": "value",
        }
    )
    assert r.object_name == "X"
