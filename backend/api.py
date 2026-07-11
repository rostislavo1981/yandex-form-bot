"""FastAPI routes for the MAX Mini App.

Endpoints (all under /api):
  GET  /api/healthz        — public, returns {ok: True}
  GET  /api/summary        — list submissions for a date range
  GET  /api/submissions/{id} — one submission with full Report
  GET  /api/screenshot/{id} — local screenshot file
  GET  /api/summary.xlsx   — Excel for a date

All non-healthz require X-Auth-InitData header (HMAC-verified).
"""
from __future__ import annotations

import logging
from datetime import date as _date
from datetime import timedelta
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, JSONResponse

from backend.config import get_settings
from backend.db import Submission, SubmissionDAO
from backend.excel.summary import build_summary
from backend.schemas import Report
from backend.webapp_auth import require_webapp_user

logger = logging.getLogger(__name__)

api_router = APIRouter(prefix="/api", tags=["miniapp"])


def _dao() -> SubmissionDAO:
    s = get_settings()
    return SubmissionDAO(s.db_full_path)


def _submission_to_dict(sub: Submission) -> dict[str, Any]:
    """Flatten a Submission row to a JSON-friendly dict for the Mini App."""
    report = sub.report
    machines = report.get("machines", [])
    personnel = report.get("personnel", {})
    return {
        "id": sub.id,
        "date": sub.date,
        "object_name": sub.object_name,
        "foreman": sub.foreman,
        "machines": machines,
        "personnel": personnel,
        "personnel_total": (
            personnel.get("itr", 0)
            + personnel.get("opr_staff", 0)
            + personnel.get("opr_external", 0)
        ),
        "waste_volume": report.get("waste_volume", 0),
        "comment": report.get("comment"),
        "final_comment": report.get("final_comment"),
        "weather": report.get("weather"),
        "screenshot_path": sub.screenshot_path,
        "screenshot_url": f"/api/screenshot/{sub.id}" if sub.screenshot_path else None,
        "disk_json_url": sub.disk_json_url,
        "disk_png_url": sub.disk_png_url,
        "filled_at": sub.filled_at,
        "confirmed": bool(sub.screenshot_path),
    }


@api_router.get("/healthz")
def healthz() -> dict[str, bool]:
    return {"ok": True}


@api_router.get("/summary", dependencies=[Depends(require_webapp_user)])
def get_summary(
    date_from: Annotated[str | None, Query(description="ISO YYYY-MM-DD, default: 7 days ago")] = None,
    date_to: Annotated[str | None, Query(description="ISO YYYY-MM-DD, default: today")] = None,
    foreman: Annotated[str | None, Query(description="Filter by foreman name")] = None,
) -> JSONResponse:
    """Return list of submissions for a date range (default last 7 days)."""
    today = _date.today()
    if not date_to:
        date_to = today.isoformat()
    if not date_from:
        date_from = (today - timedelta(days=7)).isoformat()

    # Validate dates
    try:
        _date.fromisoformat(date_to)
        _date.fromisoformat(date_from)
    except ValueError as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"bad date format: {e}"
        ) from e

    dao = _dao()
    rows = dao.list_by_date(date_from, date_to)

    if foreman:
        rows = [r for r in rows if r.foreman.lower() == foreman.lower()]

    return JSONResponse(
        {
            "date_from": date_from,
            "date_to": date_to,
            "count": len(rows),
            "submissions": [_submission_to_dict(r) for r in rows],
        }
    )


@api_router.get("/submissions/{sub_id}", dependencies=[Depends(require_webapp_user)])
def get_submission(sub_id: int) -> JSONResponse:
    dao = _dao()
    sub = dao.get_by_id(sub_id)
    if not sub:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"submission {sub_id} not found")
    return JSONResponse(_submission_to_dict(sub))


@api_router.get("/screenshot/{sub_id}", dependencies=[Depends(require_webapp_user)])
def get_screenshot(sub_id: int) -> FileResponse:
    dao = _dao()
    sub = dao.get_by_id(sub_id)
    if not sub or not sub.screenshot_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "screenshot not found")
    p = Path(sub.screenshot_path)
    if not p.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"file missing: {p}")
    return FileResponse(p, media_type="image/png", filename=p.name)


@api_router.get("/summary.xlsx", dependencies=[Depends(require_webapp_user)])
def get_summary_xlsx(
    date: Annotated[str | None, Query(description="ISO YYYY-MM-DD, default: yesterday")] = None,
) -> FileResponse:
    """Build and return Excel summary for a single day."""
    if not date:
        target = _date.today() - timedelta(days=1)
    else:
        try:
            target = _date.fromisoformat(date)
        except ValueError as e:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"bad date: {e}"
            ) from e

    dao = _dao()
    rows = dao.list_by_date(target.isoformat(), target.isoformat())
    if not rows:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"no submissions for {target.isoformat()}"
        )

    pairs = [
        (Report.model_validate(r.report), bool(r.screenshot_path)) for r in rows
    ]
    s = get_settings()
    out = s.data_dir / f"summary_{target.isoformat()}.xlsx"
    build_summary(pairs, out)
    return FileResponse(
        out,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"summary_{target.isoformat()}.xlsx",
    )
