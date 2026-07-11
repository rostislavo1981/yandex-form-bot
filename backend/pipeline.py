"""End-to-end pipeline orchestrator: foreman text -> Report -> Form -> Disk -> DB.

Stages:
1. parse_report(text)              — YandexGPT
2. fill_form(report, url, client)  — Playwright -> screenshot path
3. archive_report(client, ...)     — Yandex Disk (JSON + PNG)
4. SubmissionDAO.insert(...)       — local SQLite
5. return SubmissionResult
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path

from backend.db import SubmissionDAO
from backend.disk import YandexDiskClient
from backend.disk.archive import archive_report
from backend.forms import FormFillError, PlaywrightFormClient
from backend.forms.filler import fill_form
from backend.llm.parser import LLMPort, ParseError, parse_report
from backend.schemas import Report

logger = logging.getLogger(__name__)


@dataclass
class SubmissionResult:
    """Final result of the pipeline."""

    run_id: str
    submission_id: int | None
    report: Report
    screenshot: Path | None
    disk_json_url: str | None
    disk_png_url: str | None
    ok: bool
    error: str | None = None


async def run_pipeline(
    text: str,
    *,
    llm: LLMPort,
    form_client: PlaywrightFormClient,
    disk_client: YandexDiskClient | None,
    form_url: str,
    screenshot_dir: Path,
    dao: SubmissionDAO,
    default_foreman: str | None = None,
) -> SubmissionResult:
    """Run all 4 stages. Returns SubmissionResult even on partial failure.

    Failure modes (best-effort: don't crash, log + persist what we have):
    - parse:    raises ParseError (returns ok=False, no report)
    - fill:     FormFillError (returns ok=False, has report, no screenshot)
    - archive:  DiskError (returns ok=False, has screenshot, no urls)
    - insert:   only after a successful archive
    """
    run_id = uuid.uuid4().hex[:12]
    log = logger.getChild(run_id)

    # Stage 1: parse
    try:
        report = await parse_report(text, llm, default_foreman=default_foreman)
    except ParseError as e:
        log.error("parse failed: %s", e)
        return SubmissionResult(
            run_id=run_id, submission_id=None, report=Report.model_validate(
                {"date": "1970-01-01", "object_name": "_FAILED_", "foreman": "_FAILED_"}
            ) if False else _empty_report(),
            screenshot=None, disk_json_url=None, disk_png_url=None,
            ok=False, error=f"parse: {e}",
        )

    # Stage 2: fill form
    screenshot: Path | None = None
    try:
        screenshot = await fill_form(
            report, form_url, form_client, screenshot_dir=screenshot_dir
        )
    except FormFillError as e:
        log.error("fill failed: %s", e)
        return SubmissionResult(
            run_id=run_id, submission_id=None, report=report, screenshot=None,
            disk_json_url=None, disk_png_url=None, ok=False, error=f"fill: {e}",
        )

    # Stage 3: archive to Disk (best-effort)
    json_url: str | None = None
    png_url: str | None = None
    if disk_client is not None:
        try:
            result = await archive_report(
                disk_client, report, screenshot, root="Яндекс Формы бот"
            )
            json_url = result["json_url"]
            png_url = result["png_url"]
        except Exception as e:  # noqa: BLE001 — best-effort
            log.warning("archive failed (continuing): %s", e)
    else:
        log.info("no disk_client; skipping archive")

    # Stage 4: insert into DB
    try:
        submission_id = await asyncio.to_thread(
            dao.insert,
            foreman=report.foreman,
            date=report.date.isoformat(),
            object_name=report.object_name,
            report=report.model_dump(mode="json"),
            screenshot_path=screenshot,
            disk_json_url=json_url,
            disk_png_url=png_url,
        )
    except Exception as e:  # noqa: BLE001 — best-effort
        log.error("db insert failed: %s", e)
        return SubmissionResult(
            run_id=run_id, submission_id=None, report=report, screenshot=screenshot,
            disk_json_url=json_url, disk_png_url=png_url, ok=False, error=f"db: {e}",
        )

    return SubmissionResult(
        run_id=run_id,
        submission_id=submission_id,
        report=report,
        screenshot=screenshot,
        disk_json_url=json_url,
        disk_png_url=png_url,
        ok=True,
    )


def _empty_report() -> Report:
    """Sentinel for a pipeline run that failed at parse stage."""
    from datetime import date

    return Report(date=date(1970, 1, 1), object_name="_FAILED_", foreman="_FAILED_")
