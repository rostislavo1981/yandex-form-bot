"""Tests for backend.forms.fields (pure, no playwright)."""
from __future__ import annotations

import pytest

from backend.forms.fields import MVP_FIELDS, all_field_names, get_field


def test_mvp_has_ten_fields() -> None:
    assert len(MVP_FIELDS) == 10


def test_all_field_names_distinct() -> None:
    names = all_field_names()
    assert len(names) == len(set(names))


def test_required_fields_present() -> None:
    names = set(all_field_names())
    required = {
        "date", "object_name", "foreman",
        "work_1_name", "work_1_volume", "work_1_unit",
        "work_2_name", "work_2_volume", "work_2_unit",
        "notes",
    }
    assert required.issubset(names)


def test_get_field_works() -> None:
    f = get_field("object_name")
    assert f.label == "Объект"
    assert f.kind == "text"
    assert "object" in f.selector


def test_get_field_unknown_raises() -> None:
    with pytest.raises(KeyError, match="work_3_name"):
        get_field("work_3_name")


def test_selectors_are_css_or_xpath() -> None:
    """MVP uses CSS; future may use XPath (//...) so accept both."""
    for f in MVP_FIELDS:
        assert f.selector.startswith("input") or f.selector.startswith("textarea") or f.selector.startswith("//")
