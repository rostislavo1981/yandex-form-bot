#!/bin/sh
# yfb-entrypoint: route docker CMD to the right CLI.
#
# Usage in docker run / compose `command:`:
#   "bot"               → long-polling bot
#   "api"               → FastAPI /healthz
#   "reminder"          → one-shot daily reminder
#   "scheduler"         → in-process daily scheduler
#   "shell"             → /bin/sh
#   anything else       → passed through to `python -m …`
#
# Examples:
#   docker compose up -d                # CMD=bot
#   docker run … yfb-bot api            # start API
#   docker run … yfb-bot reminder       # one-shot (for cron)
#   docker run … --entrypoint=yfb-entrypoint yfb-bot python -m backend.cli.run_bot
set -eu

# Collect all args; if first arg is a known service, peel it off.
if [ "$#" -eq 0 ]; then
    set -- bot
fi

TARGET="$1"
shift || true

case "$TARGET" in
    bot)
        exec python -m backend.cli.run_bot "$@"
        ;;
    api)
        exec python -m backend.cli.run_api "$@"
        ;;
    reminder)
        exec python -m backend.cli.send_reminder "$@"
        ;;
    scheduler)
        exec python -m backend.cli.scheduler "$@"
        ;;
    shell)
        exec sh "$@"
        ;;
    *)
        # raw override: e.g. "yfb-bot python -m backend.cli.run_bot"
        exec python -m "backend.cli.${TARGET}" "$@"
        ;;
esac
