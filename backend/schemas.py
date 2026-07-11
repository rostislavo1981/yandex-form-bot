"""Pydantic schemas for the Report domain — REAL Yandex Form fields.

The form «Ежедневный отчёт по технике, механизмам и персоналу» (id 6a51e57af47e73a0eca7b48c)
contains these fields:
  - date              (Дата отчёта)
  - foreman           (Прораб/Ответственный/Подрядчик) — dropdown
  - object_name       (Объект)                            — dropdown
  - comment           (Коментарий)                        — long text
  - machines: list    (Техника/механизмы — серия):
      - machine_type  (Выберите технику) — dropdown
      - unit          (Единица измерения) — short text
      - quantity      (Количество) — integer
  - waste_volume      (Вывоз грунта и строительных отходов, м³) — integer
  - personnel:
      - itr           (ИТР)
      - opr_staff     (ОПР штатные)
      - opr_external  (ОПР внештатные)
  - final_comment     (Комментарии к отчёту) — long text
"""
from __future__ import annotations

from datetime import date as _date
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MachineItem(BaseModel):
    """One line of equipment/machinery used on site today.

    `machine_type=""` is allowed at this level (parser-tolerance); Report
    filters them out via `_strip_empties`.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    machine_type: str = Field(..., max_length=200)  # e.g. "Экскаватор JCB 3CX"
    unit: str = Field(..., min_length=1, max_length=20)  # "час", "смена", "м³"
    quantity: float = Field(..., ge=0)  # integer normally, but float for safety

    def to_form_dict(self) -> dict[str, Any]:
        return {"machine_type": self.machine_type, "unit": self.unit, "quantity": self.quantity}


class Personnel(BaseModel):
    """Personnel counts on site today."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    itr: int = Field(default=0, ge=0, le=1000)  # ИТР (инженерно-технические работники)
    opr_staff: int = Field(default=0, ge=0, le=1000)  # ОПР штатные
    opr_external: int = Field(default=0, ge=0, le=1000)  # ОПР внештатные

    @property
    def total(self) -> int:
        return self.itr + self.opr_staff + self.opr_external


class Report(BaseModel):
    """Structured foreman daily report — REAL form schema."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    date: _date
    foreman: str = Field(..., min_length=1, max_length=200)
    object_name: str = Field(..., min_length=1, max_length=300)
    comment: str | None = Field(default=None, max_length=2000)
    machines: list[MachineItem] = Field(default_factory=list, max_length=20)
    waste_volume: float = Field(default=0.0, ge=0)  # м³
    personnel: Personnel = Field(default_factory=Personnel)
    final_comment: str | None = Field(default=None, max_length=2000)
    weather: str | None = Field(default=None, max_length=200)

    @field_validator("date", mode="before")
    @classmethod
    def _parse_date(cls, v: Any) -> Any:
        """Accept 'YYYY-MM-DD' or full ISO datetime; coerce to date."""
        if isinstance(v, _date) and not isinstance(v, datetime):
            return v
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, str):
            s = v.strip()
            try:
                return _date.fromisoformat(s)
            except ValueError:
                pass
            try:
                return datetime.fromisoformat(s).date()
            except ValueError as e:
                raise ValueError(f"Invalid date string: {v!r}") from e
        raise ValueError(f"date must be date|datetime|str, got {type(v).__name__}")

    @model_validator(mode="after")
    def _strip_empties(self) -> Report:
        # Drop machines with empty machine_type (parser tolerance)
        self.machines = [m for m in self.machines if m.machine_type and m.machine_type.strip()]
        return self

    def to_form_payload(self) -> dict[str, Any]:
        """Flatten to the actual 12 form fields.

        Real form structure:
          - 1 date field
          - 3 dropdowns: foreman, object, plus dropdown for first machine
          - 1 long text: comment
          - 3 machine subfields (x N machines, but MVP form has 1 series slot)
          - 1 integer: waste_volume
          - 3 personnel integers
          - 1 long text: final_comment

        MVP form has 1 series slot (the «Серия вопросов Техника/механизмы»).
        Excess machines are appended to the comment in a structured form.
        """
        payload: dict[str, Any] = {
            "date": self.date.isoformat(),
            "foreman": self.foreman,
            "object": self.object_name,
            "comment": self.comment or "",
        }

        # First machine goes into the form's 1 series slot
        if self.machines:
            m = self.machines[0]
            payload["machine_type"] = m.machine_type
            payload["machine_unit"] = m.unit
            payload["machine_quantity"] = m.quantity
        else:
            payload["machine_type"] = ""
            payload["machine_unit"] = "час"
            payload["machine_quantity"] = 0

        payload["waste_volume"] = self.waste_volume
        payload["itr"] = self.personnel.itr
        payload["opr_staff"] = self.personnel.opr_staff
        payload["opr_external"] = self.personnel.opr_external
        payload["final_comment"] = self.final_comment or ""

        # Excess machines -> packed into comment (only if there are >1)
        if len(self.machines) > 1:
            extras = "; ".join(
                f"{m.machine_type} {m.quantity:g} {m.unit}" for m in self.machines[1:]
            )
            existing = payload["comment"]
            payload["comment"] = (
                f"{existing} | доп. техника: {extras}" if existing else f"доп. техника: {extras}"
            ).strip(" |")

        return payload
