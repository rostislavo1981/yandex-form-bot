"""High-level form filler: Report -> submission screenshot.

Sequence:
1. goto(form_url)
2. for each MVP field, fill(selector, value from report.to_form_payload())
3. submit()
4. screenshot(out_path)
5. return out_path as submission_id

Skips fields whose value is None or empty string (so a half-filled report
doesn't overwrite the form with blanks).
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.forms import PlaywrightFormClient
from backend.forms.fields import MVP_FIELDS
from backend.schemas import Report

logger = logging.getLogger(__name__)


def value_to_str(v: Any) -> str:
    """Render a form value, defending against str(None).strip()=='None' bug."""
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


async def fill_form(
    report: Report,
    form_url: str,
    client: PlaywrightFormClient,
    *,
    screenshot_dir: Path,
    screenshot_name: str | None = None,
) -> Path:
    """Fill the form, return path to the post-submit screenshot.

    Raises FormFillError on any failure (selector missing, submit failed, etc.).
    """
    payload = report.to_form_payload()
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    if not screenshot_name:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_name = f"{report.date.isoformat()}_{report.foreman}_{ts}.png"
    out_path = screenshot_dir / screenshot_name

    await client.goto(form_url)

    # Fill in declared order
    for field_def in MVP_FIELDS:
        raw = payload.get(field_def.name)
        s = value_to_str(raw)
        if not s:
            # Skip empty values so we don't overwrite user input
            logger.info("fill_form: skip %s (empty value)", field_def.name)
            continue
        await client.fill(field_def.selector, s)

    await client.submit()
    await client.screenshot(out_path)
    logger.info("fill_form: ok -> %s", out_path)
    return out_path
