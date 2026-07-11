"""Real form field map — «Ежедневный отчёт по технике, механизмам и персоналу».

Form: https://forms.yandex.ru/admin/6a51e57af47e73a0eca7b48c/edit
Currently 12 fields, target 142.

When the form is published, the selectors here will be tuned against the
real DOM. For now they are best-guess placeholders (input[name=...]).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FormField:
    """One form input."""

    name: str
    selector: str
    kind: str = "text"  # text | number | date | textarea | select
    label: str = ""


# 12 fields, in fill order.
# NOTE: «ИТР», «ОПР (штатные)», «ОПР (внештатные)» — each is a separate integer
# input in the real form (Yandex Forms renders "Целое число" as <input type=number>).
MVP_FIELDS: tuple[FormField, ...] = (
    FormField("date", 'input[name="date"]', "date", "Дата отчёта"),
    FormField("foreman", 'select[name="foreman"], input[name="foreman"]', "select", "Прораб"),
    FormField("object", 'select[name="object"], input[name="object"]', "select", "Объект"),
    FormField("comment", 'textarea[name="comment"]', "textarea", "Комментарий"),
    FormField("machine_type", 'input[name="machine_type"]', "text", "Техника — название"),
    FormField("machine_unit", 'input[name="machine_unit"]', "text", "Единица"),
    FormField("machine_quantity", 'input[name="machine_quantity"]', "number", "Количество"),
    FormField("waste_volume", 'input[name="waste_volume"]', "number", "Вывоз грунта, м³"),
    FormField("itr", 'input[name="itr"]', "number", "ИТР"),
    FormField("opr_staff", 'input[name="opr_staff"]', "number", "ОПР штатные"),
    FormField("opr_external", 'input[name="opr_external"]', "number", "ОПР внештатные"),
    FormField("final_comment", 'textarea[name="final_comment"]', "textarea", "Итоговый комментарий"),
)


SUBMIT_SELECTOR = 'button[type="submit"], input[type="submit"]'


def get_field(name: str) -> FormField:
    for f in MVP_FIELDS:
        if f.name == name:
            return f
    raise KeyError(f"Unknown MVP form field: {name!r}. Known: {[f.name for f in MVP_FIELDS]}")


def all_field_names() -> list[str]:
    return [f.name for f in MVP_FIELDS]
