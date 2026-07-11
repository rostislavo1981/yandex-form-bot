"""Tests for backend.forms.fields — REAL form (12 fields)."""
from __future__ import annotations

import pytest

from backend.forms.fields import MVP_FIELDS, all_field_names, get_field


def test_mvp_has_twelve_fields() -> None:
    assert len(MVP_FIELDS) == 12


def test_all_field_names_distinct() -> None:
    names = all_field_names()
    assert len(names) == len(set(names))


def test_required_fields_present() -> None:
    names = set(all_field_names())
    required = {
        "date", "foreman", "object", "comment",
        "machine_type", "machine_unit", "machine_quantity",
        "waste_volume", "itr", "opr_staff", "opr_external", "final_comment",
    }
    assert required == names, f"missing or extra: {required ^ names}"


def test_get_field_works() -> None:
    f = get_field("waste_volume")
    assert f.label == "Вывоз грунта, м³"
    assert f.kind == "number"


def test_get_field_unknown_raises() -> None:
    with pytest.raises(KeyError, match="work_1_name"):
        get_field("work_1_name")  # OLD form field, should not exist


def test_selectors_are_css() -> None:
    for f in MVP_FIELDS:
        assert f.selector.startswith("input") or f.selector.startswith("textarea") or f.selector.startswith("select")
