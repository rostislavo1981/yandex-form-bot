"""SQLite DAO for submission records.

Schema:
    submissions (
        id INTEGER PK AUTOINCREMENT,
        foreman TEXT NOT NULL,
        date TEXT NOT NULL,         -- ISO YYYY-MM-DD
        object_name TEXT NOT NULL,
        report_json TEXT NOT NULL,  -- full Report.model_dump_json
        screenshot_path TEXT,       -- local path
        disk_json_url TEXT,
        disk_png_url TEXT,
        filled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )

The DAO is sync (sqlite3 is sync) — call from async code via asyncio.to_thread.
"""
from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    foreman TEXT NOT NULL,
    date TEXT NOT NULL,
    object_name TEXT NOT NULL,
    report_json TEXT NOT NULL,
    screenshot_path TEXT,
    disk_json_url TEXT,
    disk_png_url TEXT,
    filled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_submissions_date ON submissions(date);
CREATE INDEX IF NOT EXISTS idx_submissions_foreman ON submissions(foreman);
"""


@dataclass
class Submission:
    """Lightweight value-object for a DB row."""

    id: int
    foreman: str
    date: str
    object_name: str
    report: dict[str, Any]
    screenshot_path: str | None
    disk_json_url: str | None
    disk_png_url: str | None
    filled_at: str

    def to_report_json(self) -> str:
        return json.dumps(self.report, ensure_ascii=False, indent=2)


class SubmissionDAO:
    """Sync DAO. Not thread-safe; one instance per request/job."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        c = self._connect()
        try:
            yield c
            c.commit()
        finally:
            c.close()

    def _init_schema(self) -> None:
        with self._conn() as c:
            c.executescript(SCHEMA)

    def insert(
        self,
        *,
        foreman: str,
        date: str,
        object_name: str,
        report: dict[str, Any],
        screenshot_path: Path | None = None,
        disk_json_url: str | None = None,
        disk_png_url: str | None = None,
    ) -> int:
        with self._conn() as c:
            cur = c.execute(
                """INSERT INTO submissions
                   (foreman, date, object_name, report_json, screenshot_path,
                    disk_json_url, disk_png_url)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    foreman,
                    date,
                    object_name,
                    json.dumps(report, ensure_ascii=False),
                    str(screenshot_path) if screenshot_path else None,
                    disk_json_url,
                    disk_png_url,
                ),
            )
            return int(cur.lastrowid)

    def list_by_date(
        self, date_from: str, date_to: str
    ) -> list[Submission]:
        with self._conn() as c:
            rows = c.execute(
                """SELECT * FROM submissions
                   WHERE date BETWEEN ? AND ?
                   ORDER BY date ASC, id ASC""",
                (date_from, date_to),
            ).fetchall()
        return [_row_to_submission(r) for r in rows]

    def list_recent(self, limit: int = 50) -> list[Submission]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM submissions ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [_row_to_submission(r) for r in rows]

    def get_by_id(self, sid: int) -> Submission | None:
        with self._conn() as c:
            row = c.execute(
                "SELECT * FROM submissions WHERE id = ?", (sid,)
            ).fetchone()
        return _row_to_submission(row) if row else None


def _row_to_submission(row: sqlite3.Row) -> Submission:
    return Submission(
        id=row["id"],
        foreman=row["foreman"],
        date=row["date"],
        object_name=row["object_name"],
        report=json.loads(row["report_json"]),
        screenshot_path=row["screenshot_path"],
        disk_json_url=row["disk_json_url"],
        disk_png_url=row["disk_png_url"],
        filled_at=row["filled_at"],
    )
