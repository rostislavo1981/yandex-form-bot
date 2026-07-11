"""CLI entry: python -m backend.cli.run_bot"""
from __future__ import annotations

import asyncio
import sys

from backend.max.bot import run_bot


def main() -> int:
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"bot failed: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
