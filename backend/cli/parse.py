"""CLI: parse a text file into JSON Report using YandexGPT.

Usage:
    python -m backend.cli.parse path/to/report.txt
    python -m backend.cli.parse path/to/report.txt --default-foreman Степанов
    python -m backend.cli.parse path/to/report.txt --output out.json

Reads YANDEX_GPT_API_KEY, YANDEX_GPT_FOLDER_ID from env (or .env).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from backend.config import get_settings
from backend.llm.client import YandexGPTClient
from backend.llm.parser import ParseError, parse_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse a foreman report via YandexGPT")
    parser.add_argument("input", type=Path, help="Path to .txt file with foreman report")
    parser.add_argument(
        "--default-foreman", default=None, help="Override default foreman name"
    )
    parser.add_argument(
        "--output", "-o", type=Path, default=None, help="Write JSON here (default: stdout)"
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress progress logs on stderr"
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: file not found: {args.input}", file=sys.stderr)
        return 2

    text = args.input.read_text(encoding="utf-8")
    return asyncio.run(_run(text, args))


async def _run(text: str, args: argparse.Namespace) -> int:
    s = get_settings()
    if not s.yandex_gpt_api_key or not s.yandex_gpt_folder_id:
        print(
            "ERROR: YANDEX_GPT_API_KEY and YANDEX_GPT_FOLDER_ID must be set",
            file=sys.stderr,
        )
        return 3

    client = YandexGPTClient(
        api_key=s.yandex_gpt_api_key,
        folder_id=s.yandex_gpt_folder_id,
        model=s.yandex_gpt_model,
        max_tokens=s.yandex_gpt_max_tokens,
    )
    try:
        report = await parse_report(
            text,
            client,
            default_foreman=args.default_foreman or s.default_foreman,
        )
    except ParseError as e:
        print(f"ERROR: parse failed: {e}", file=sys.stderr)
        return 4
    finally:
        await client.close()

    out = json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(out, encoding="utf-8")
        if not args.quiet:
            print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
