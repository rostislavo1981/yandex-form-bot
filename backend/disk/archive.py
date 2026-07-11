"""High-level archive: write Report JSON + screenshot to Disk.

Layout: /<root>/<YYYY-MM-DD>/<foreman>_<timestamp>.json
        /<root>/<YYYY-MM-DD>/<foreman>_<timestamp>.png
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from backend.disk import YandexDiskClient
from backend.schemas import Report

logger = logging.getLogger(__name__)


def _safe_name(s: str) -> str:
    """Foreman name → disk-safe filename token."""
    return "".join(c for c in s if c.isalnum() or c in ("-", "_")) or "foreman"


async def archive_report(
    client: YandexDiskClient,
    report: Report,
    screenshot: Path,
    *,
    root: str,
) -> dict[str, str]:
    """Upload Report JSON + screenshot to <root>/<date>/<foreman>_<ts>.{json,png}.

    Returns {"json_url": ..., "png_url": ..., "json_path": ..., "png_path": ...}
    """
    date_str = report.date.isoformat()
    ts = datetime.now().strftime("%H%M%S")
    base = f"{_safe_name(report.foreman)}_{ts}"
    folder_path = f"/{root}/{date_str}"
    json_remote = f"{folder_path}/{base}.json"
    png_remote = f"{folder_path}/{base}.png"

    # Idempotent folder create
    await client.ensure_folder(folder_path)

    # Write JSON to a temp file, then upload
    import json as _json
    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", encoding="utf-8", delete=False
    ) as tmp:
        tmp.write(_json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))
        tmp_path = Path(tmp.name)
    try:
        json_url = await client.upload_file(json_remote, tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    png_url = await client.upload_file(png_remote, screenshot)

    return {
        "json_url": json_url,
        "png_url": png_url,
        "json_path": json_remote,
        "png_path": png_remote,
    }
