"""MVP field map for the Yandex Form.

The form at forms.yandex.ru/admin/6a51e57af47e73a0eca7b48c (today 7 questions,
target 142) — for MVP we only fill the 10 most common fields.

Field name -> CSS selector / XPath hint. Real selectors will be discovered
when the form is published. The map is intentionally a single source of
truth so when the form changes, only this file is updated.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FormField:
    """One form input."""

    name: str  # logical name (matches Report.to_form_payload keys)
    selector: str  # CSS or XPath; we use CSS in MVP
    kind: str = "text"  # text | number | date | textarea
    label: str = ""  # human-readable, for logs/errors


# MVP: 10 fields. Order matters for the fill sequence.
MVP_FIELDS: tuple[FormField, ...] = (
    FormField("date", 'input[name="date"]', "date", "Дата отчёта"),
    FormField("object_name", 'input[name="object"]', "text", "Объект"),
    FormField("foreman", 'input[name="foreman"]', "text", "Прораб"),
    FormField("work_1_name", 'input[name="work_1_name"]', "text", "Работа 1 — название"),
    FormField("work_1_volume", 'input[name="work_1_volume"]', "number", "Работа 1 — объём"),
    FormField("work_1_unit", 'input[name="work_1_unit"]', "text", "Работа 1 — ед."),
    FormField("work_2_name", 'input[name="work_2_name"]', "text", "Работа 2 — название"),
    FormField("work_2_volume", 'input[name="work_2_volume"]', "number", "Работа 2 — объём"),
    FormField("work_2_unit", 'input[name="work_2_unit"]', "text", "Работа 2 — ед."),
    FormField("notes", 'textarea[name="notes"]', "textarea", "Заметки"),
)


SUBMIT_SELECTOR = 'button[type="submit"], input[type="submit"]'


def get_field(name: str) -> FormField:
    """Lookup a field by logical name. Raises KeyError if missing."""
    for f in MVP_FIELDS:
        if f.name == name:
            return f
    raise KeyError(f"Unknown MVP form field: {name!r}. Known: {[f.name for f in MVP_FIELDS]}")


def all_field_names() -> list[str]:
    return [f.name for f in MVP_FIELDS]
