"""Tests for backend.schemas.Report — REAL form schema."""
from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from backend.schemas import MachineItem, Personnel, Report


def test_minimal_report_valid() -> None:
    r = Report(date="2026-07-10", foreman="Степанов", object_name="РП-7 Каменка")
    assert r.date == date(2026, 7, 10)
    assert r.foreman == "Степанов"
    assert r.object_name == "РП-7 Каменка"
    assert r.machines == []
    assert r.personnel.itr == 0
    assert r.waste_volume == 0.0
    assert r.comment is None


def test_date_accepts_datetime_string() -> None:
    r = Report(date="2026-07-10T15:30:00", foreman="X", object_name="Y")
    assert r.date == date(2026, 7, 10)


def test_invalid_date_raises() -> None:
    with pytest.raises(ValidationError) as exc:
        Report(date="not-a-date", foreman="X", object_name="Y")
    assert "date" in str(exc.value).lower()


def test_full_report_with_machines_and_personnel() -> None:
    r = Report(
        date="2026-07-10",
        foreman="Степанов",
        object_name="РП-7 Каменка",
        comment="Кабель привезли вовремя",
        machines=[
            MachineItem(machine_type="Экскаватор JCB 3CX", unit="час", quantity=8),
            MachineItem(machine_type="Кран автомобильный", unit="смена", quantity=1),
        ],
        waste_volume=15.0,
        personnel=Personnel(itr=1, opr_staff=4, opr_external=2),
        final_comment="Без замечаний",
        weather="ясно, +22",
    )
    assert len(r.machines) == 2
    assert r.personnel.total == 7
    assert r.waste_volume == 15.0


def test_machine_rejects_negative_quantity() -> None:
    with pytest.raises(ValidationError):
        MachineItem(machine_type="X", unit="час", quantity=-1)


def test_machine_rejects_blank_type() -> None:
    """machine_type is required (it's the 'name' of the machine)."""
    with pytest.raises(ValidationError):
        MachineItem(machine_type="", unit="час", quantity=1)


def test_empty_machines_filtered() -> None:
    r = Report(
        date="2026-07-10",
        foreman="X",
        object_name="Y",
        machines=[
            MachineItem(machine_type="  ", unit="час", quantity=1),
            MachineItem(machine_type="Экскаватор", unit="час", quantity=4),
        ],
    )
    assert len(r.machines) == 1
    assert r.machines[0].machine_type == "Экскаватор"


def test_personnel_total() -> None:
    p = Personnel(itr=2, opr_staff=5, opr_external=3)
    assert p.total == 10


def test_to_form_payload_one_machine() -> None:
    r = Report(
        date="2026-07-10",
        foreman="Степанов",
        object_name="РП-7",
        machines=[MachineItem(machine_type="Экскаватор JCB", unit="час", quantity=8)],
        waste_volume=10.0,
        personnel=Personnel(itr=1, opr_staff=4, opr_external=0),
        final_comment="ок",
    )
    p = r.to_form_payload()
    assert p["date"] == "2026-07-10"
    assert p["foreman"] == "Степанов"
    assert p["object"] == "РП-7"
    assert p["machine_type"] == "Экскаватор JCB"
    assert p["machine_unit"] == "час"
    assert p["machine_quantity"] == 8
    assert p["waste_volume"] == 10
    assert p["itr"] == 1
    assert p["opr_staff"] == 4
    assert p["opr_external"] == 0
    assert p["final_comment"] == "ок"
    # No extra machines
    assert "доп. техника" not in p["comment"]


def test_to_form_payload_two_machines_extras_in_comment() -> None:
    r = Report(
        date="2026-07-10",
        foreman="X",
        object_name="Y",
        machines=[
            MachineItem(machine_type="A", unit="час", quantity=4),
            MachineItem(machine_type="B", unit="смена", quantity=1),
        ],
    )
    p = r.to_form_payload()
    assert p["machine_type"] == "A"
    assert "B 1 смена" in p["comment"]


def test_to_form_payload_no_machines() -> None:
    r = Report(date="2026-07-10", foreman="X", object_name="Y")
    p = r.to_form_payload()
    assert p["machine_type"] == ""
    assert p["machine_quantity"] == 0
    assert p["machine_unit"] == "час"


def test_extra_fields_ignored() -> None:
    r = Report.model_validate(
        {
            "date": "2026-07-10",
            "foreman": "X",
            "object_name": "Y",
            "future_field": "value",
        }
    )
    assert r.foreman == "X"


def test_personnel_rejects_negative() -> None:
    with pytest.raises(ValidationError):
        Personnel(itr=-1, opr_staff=0, opr_external=0)
