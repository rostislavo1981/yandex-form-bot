"""CLI: take a Report JSON, fill the Yandex Form, save screenshot.

Usage:
    python -m backend.cli.fill_form --report report.json
    python -m backend.cli.fill_form --text "10.07.2026 РП-7 Степанов Копка 50 м" --parse

Reads FORM_PUBLISHED_URL from env.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from backend.config import get_settings
from backend.forms import FakePlaywrightClient, FormFillError, RealPlaywrightClient
from backend.forms.filler import fill_form
from backend.schemas import Report


def main() -> int:
    parser = argparse.ArgumentParser(description="Fill Yandex Form with a Report")
    parser.add_argument("--report", "-r", type=Path, help="Path to Report JSON")
    parser.add_argument("--text", "-t", type=str, help="Foreman text (requires --parse)")
    parser.add_argument("--parse", action="store_true", help="Parse --text via YandexGPT first")
    parser.add_argument(
        "--url", type=str, default=None, help="Override FORM_PUBLISHED_URL"
    )
    parser.add_argument(
        "--screenshot-dir",
        type=Path,
        default=None,
        help="Where to save the screenshot (default: DATA_DIR/submissions)",
    )
    parser.add_argument(
        "--fake", action="store_true", help="Use FakePlaywrightClient (for tests)"
    )
    args = parser.parse_args()

    if not args.report and not args.text:
        print("ERROR: provide --report or --text", file=sys.stderr)
        return 2
    if args.text and not args.parse:
        print("ERROR: --text requires --parse", file=sys.stderr)
        return 2

    s = get_settings()
    url = args.url or s.form_published_url
    if not url:
        print("ERROR: FORM_PUBLISHED_URL is not set", file=sys.stderr)
        return 3
    ss_dir = args.screenshot_dir or (s.data_dir / "submissions")

    if args.report:
        if not args.report.exists():
            print(f"ERROR: file not found: {args.report}", file=sys.stderr)
            return 2
        report = Report.model_validate_json(args.report.read_text(encoding="utf-8"))
    else:
        # Lazy import parser to avoid hard YandexGPT dep
        from backend.llm.client import YandexGPTClient
        from backend.llm.parser import ParseError, parse_report

        if not s.yandex_gpt_api_key or not s.yandex_gpt_folder_id:
            print("ERROR: YandexGPT creds missing for --parse", file=sys.stderr)
            return 3
        client = YandexGPTClient(
            api_key=s.yandex_gpt_api_key,
            folder_id=s.yandex_gpt_folder_id,
            model=s.yandex_gpt_model,
        )
        try:
            report = asyncio.run(
                parse_report(args.text or "", client, default_foreman=s.default_foreman)
            )
        except ParseError as e:
            print(f"ERROR: parse failed: {e}", file=sys.stderr)
            return 4
        finally:
            asyncio.run(client.close())

    return asyncio.run(_run_fill(report, url, ss_dir, args.fake))


async def _run_fill(report: Report, url: str, ss_dir: Path, fake: bool) -> int:
    client_ctx = (
        FakePlaywrightClient() if fake else _real_client()
    )
    if fake:
        try:
            out = await fill_form(report, url, client_ctx, screenshot_dir=ss_dir)
        except FormFillError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 5
        await client_ctx.close()
        print(json.dumps({"screenshot": str(out), "report": report.model_dump(mode="json")}, ensure_ascii=False))
        return 0
    else:
        try:
            async with client_ctx as c:
                out = await fill_form(report, url, c, screenshot_dir=ss_dir)
        except FormFillError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 5
        print(json.dumps({"screenshot": str(out), "report": report.model_dump(mode="json")}, ensure_ascii=False))
        return 0


def _real_client() -> RealPlaywrightClient:
    s = get_settings()
    return RealPlaywrightClient(
        headless=True,
        user_data_dir=s.data_dir / "chromium",
    )


if __name__ == "__main__":
    sys.exit(main())
