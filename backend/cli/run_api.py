"""CLI entry: python -m backend.cli.run_api — uvicorn dev server."""
from __future__ import annotations

import sys

import uvicorn


def main() -> int:
    uvicorn.run(
        "backend.app:create_app",
        factory=True,
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
