"""Tests for backend.db (SubmissionDAO)."""
from __future__ import annotations

from pathlib import Path

from backend.db import SubmissionDAO
from backend.schemas import Report


def _make_report_dict(foreman: str = "Степанов", object_name: str = "РП-7") -> dict:
    r = Report(
        date="2026-07-10",
        object_name=object_name,
        foreman=foreman,
        machines=[{"machine_type": "Экскаватор", "unit": "час", "quantity": 5}],
        waste_volume=10.0,
        personnel={"itr": 1, "opr_staff": 3, "opr_external": 0},
    )
    return r.model_dump(mode="json")


def test_insert_and_get_by_id(tmp_path: Path) -> None:
    dao = SubmissionDAO(tmp_path / "test.db")
    sid = dao.insert(
        foreman="Степанов",
        date="2026-07-10",
        object_name="РП-7",
        report=_make_report_dict(),
        screenshot_path=tmp_path / "s.png",
        disk_json_url="https://disk.yandex.ru/j",
        disk_png_url="https://disk.yandex.ru/p",
    )
    assert sid >= 1
    s = dao.get_by_id(sid)
    assert s is not None
    assert s.foreman == "Степанов"
    assert s.date == "2026-07-10"
    assert s.screenshot_path == str(tmp_path / "s.png")
    assert s.disk_json_url == "https://disk.yandex.ru/j"
    assert s.report["object_name"] == "РП-7"


def test_list_by_date_range(tmp_path: Path) -> None:
    dao = SubmissionDAO(tmp_path / "test.db")
    for d in ["2026-07-08", "2026-07-10", "2026-07-12"]:
        dao.insert(
            foreman="X",
            date=d,
            object_name="Y",
            report=_make_report_dict(),
        )
    rows = dao.list_by_date("2026-07-09", "2026-07-11")
    assert len(rows) == 1
    assert rows[0].date == "2026-07-10"


def test_list_recent_ordering(tmp_path: Path) -> None:
    dao = SubmissionDAO(tmp_path / "test.db")
    for i in range(5):
        dao.insert(
            foreman="X",
            date="2026-07-10",
            object_name=f"obj_{i}",
            report=_make_report_dict(),
        )
    rows = dao.list_recent(limit=3)
    assert len(rows) == 3
    # Most recent first
    assert rows[0].id > rows[1].id > rows[2].id


def test_get_by_id_missing_returns_none(tmp_path: Path) -> None:
    dao = SubmissionDAO(tmp_path / "test.db")
    assert dao.get_by_id(9999) is None


def test_schema_init_idempotent(tmp_path: Path) -> None:
    """Init twice must not raise."""
    SubmissionDAO(tmp_path / "test.db")
    SubmissionDAO(tmp_path / "test.db")  # noqa: F841 — smoke


def test_report_json_round_trip(tmp_path: Path) -> None:
    """Insert with full report, retrieve, validate as Report."""
    from backend.schemas import Report

    dao = SubmissionDAO(tmp_path / "test.db")
    sid = dao.insert(
        foreman="Казнадеев",
        date="2026-07-10",
        object_name="ТП-345",
        report=_make_report_dict(foreman="Казнадеев", object_name="ТП-345"),
    )
    s = dao.get_by_id(sid)
    r = Report.model_validate(s.report)
    assert r.foreman == "Казнадеев"
    assert r.machines[0].machine_type == "Экскаватор"
