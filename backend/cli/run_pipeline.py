"""CLI entry: python -m backend.cli.run_pipeline path/to/report.txt"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from backend.config import get_settings
from backend.db import SubmissionDAO
from backend.disk import YandexDiskClient
from backend.forms import FakePlaywrightClient
from backend.llm.client import YandexGPTClient
from backend.pipeline import run_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the full pipeline on a foreman text file")
    parser.add_argument("input", type=Path, help="Path to .txt with foreman report")
    parser.add_argument("--output", "-o", type=Path, help="Write SubmissionResult JSON here")
    parser.add_argument(
        "--fake-form", action="store_true", help="Use FakePlaywrightClient (no real browser)"
    )
    parser.add_argument(
        "--no-disk", action="store_true", help="Skip Yandex Disk archive stage"
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: file not found: {args.input}", file=sys.stderr)
        return 2

    s = get_settings()
    if not s.yandex_gpt_api_key or not s.yandex_gpt_folder_id:
        print("ERROR: YANDEX_GPT creds missing", file=sys.stderr)
        return 3
    if not args.fake_form and not s.form_published_url:
        print("ERROR: FORM_PUBLISHED_URL missing (or use --fake-form)", file=sys.stderr)
        return 3

    text = args.input.read_text(encoding="utf-8")
    return asyncio.run(_run_pipeline(text, s, args))


async def _run_pipeline(text: str, s: Any, args: argparse.Namespace) -> int:
    llm = YandexGPTClient(
        api_key=s.yandex_gpt_api_key,
        folder_id=s.yandex_gpt_folder_id,
        model=s.yandex_gpt_model,
    )
    if args.fake_form:
        form_client: Any = FakePlaywrightClient()
        close_form = True
    else:
        from backend.forms.playwright_real import RealPlaywrightClient

        form_client = RealPlaywrightClient(
            headless=True, user_data_dir=s.data_dir / "chromium"
        )
        close_form = True
    disk_client: YandexDiskClient | None = None
    if not args.no_disk and s.yandex_disk_oauth_token:
        disk_client = YandexDiskClient(
            oauth_token=s.yandex_disk_oauth_token,
            refresh_token=s.yandex_disk_refresh_token,
            client_id=s.yandex_disk_client_id,
            client_secret=s.yandex_disk_client_secret,
        )
    dao = SubmissionDAO(s.db_full_path)
    screenshot_dir = s.data_dir / "submissions"
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    try:
        if hasattr(form_client, "__aenter__"):
            async with form_client as fc:
                res = await run_pipeline(
                    text,
                    llm=llm,
                    form_client=fc,
                    disk_client=disk_client,
                    form_url=s.form_published_url or "https://example.com",
                    screenshot_dir=screenshot_dir,
                    dao=dao,
                    default_foreman=s.default_foreman,
                )
        else:
            res = await run_pipeline(
                text,
                llm=llm,
                form_client=form_client,
                disk_client=disk_client,
                form_url=s.form_published_url or "https://example.com",
                screenshot_dir=screenshot_dir,
                dao=dao,
                default_foreman=s.default_foreman,
            )
    finally:
        await llm.close()
        if disk_client is not None:
            await disk_client.close()
        if close_form and hasattr(form_client, "close") and not hasattr(form_client, "__aenter__"):
            await form_client.close()

    out = {
        "ok": res.ok,
        "run_id": res.run_id,
        "submission_id": res.submission_id,
        "error": res.error,
        "screenshot": str(res.screenshot) if res.screenshot else None,
        "disk_json_url": res.disk_json_url,
        "disk_png_url": res.disk_png_url,
        "report": res.report.model_dump(mode="json"),
    }
    serialized = json.dumps(out, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(serialized, encoding="utf-8")
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(serialized)
    return 0 if res.ok else 5


if __name__ == "__main__":
    sys.exit(main())
