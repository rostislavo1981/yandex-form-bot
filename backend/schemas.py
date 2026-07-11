"""Pydantic schemas for the Report domain.

A Report is a structured representation of one foreman's daily text report.
It's the contract between parser (YandexGPT) and downstream (form filler, disk, excel).
"""
from __future__ import annotations

from datetime import date as _date
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class WorkItem(BaseModel):
    """One line item: e.g. 'копка траншеи — 50 м'.

    Empty `name` is allowed here so the parser doesn't crash on GPT junk.
    They are filtered out at the Report level via _strip_empties.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(..., max_length=200)
    volume: float = Field(..., ge=0)
    unit: str = Field(..., min_length=1, max_length=20)
    people_count: int | None = Field(default=None, ge=0, le=1000)

    def to_form_dict(self) -> dict[str, Any]:
        """Flatten for form filling: {name, volume, unit, people_count}."""
        return {
            "name": self.name,
            "volume": self.volume,
            "unit": self.unit,
            "people_count": self.people_count,
        }


class Material(BaseModel):
    """One material line: e.g. 'кабель АПвПу-10 3x120 — 200 м'."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=200)
    qty: float = Field(..., ge=0)
    unit: str = Field(..., min_length=1, max_length=20)


class Report(BaseModel):
    """Top-level structured foreman report for a single day.

    field_validator on `date` accepts both date and datetime ISO strings
    (YandexGPT sometimes returns datetimes with time component).
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    date: _date
    object_name: str = Field(..., min_length=1, max_length=300)
    foreman: str = Field(..., min_length=1, max_length=100)
    works: list[WorkItem] = Field(default_factory=list, max_length=50)
    materials: list[Material] = Field(default_factory=list, max_length=50)
    notes: str | None = Field(default=None, max_length=2000)
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
            # Try date first, then datetime
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
        # Drop works/materials with empty names after strip
        self.works = [w for w in self.works if w.name]
        self.materials = [m for m in self.materials if m.name]
        return self

    def to_form_payload(self) -> dict[str, Any]:
        """Flatten to {date, object_name, foreman, work_1_*, work_2_*, ...} for MVP form.

        MVP form has slots for 2 works. Excess works are joined into notes.
        """
        payload: dict[str, Any] = {
            "date": self.date.isoformat(),
            "object_name": self.object_name,
            "foreman": self.foreman,
            "notes": self.notes or "",
        }
        for i, work in enumerate(self.works[:2], start=1):
            payload[f"work_{i}_name"] = work.name
            payload[f"work_{i}_volume"] = work.volume
            payload[f"work_{i}_unit"] = work.unit
            payload[f"work_{i}_people"] = work.people_count
        # If only 1 work, leave work_2 empty rather than echoing
        if len(self.works) < 2:
            payload.setdefault("work_2_name", "")
            payload.setdefault("work_2_volume", 0.0)
            payload.setdefault("work_2_unit", "")
            payload.setdefault("work_2_people", None)
        if len(self.works) > 2:
            extra = "; ".join(
                # Format volume without trailing .0 for whole numbers
                f"{w.name} {w.volume:g} {w.unit}" for w in self.works[2:]
            )
            payload["notes"] = (payload["notes"] + " | доп. работы: " + extra).strip(" |")
        return payload
