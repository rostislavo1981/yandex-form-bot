"""CLI entry: python -m backend.cli.send_reminder

Sends a one-shot reminder to all subscribers. Designed to be run from
cron / launchd. See backend.cli.send_reminder for details.
"""
from __future__ import annotations

import sys

from backend.cli.send_reminder import main

if __name__ == "__main__":
    sys.exit(main())
