# MAX Daily Report

FastAPI backend + Vite React frontend for daily construction reports inside the
[MAX](https://max.ru) messenger.

## Local development

```bash
make install       # create venv, install deps, copy .env.example to .env
make db-up         # start PostgreSQL in Docker
make test          # pytest
make lint          # ruff
make api           # uvicorn --reload on :8000
```

Fill `.env` with `MAX_BOT_TOKEN`, `MAX_WEBHOOK_SECRET`, `MAX_GROUP_ID` before
using real MAX features. Dev mode (`DEBUG=true APP_ENV=dev`) bypasses MAX
auth and auto-creates a placeholder user.

## Production deploy

Target: a clean VPS with Docker Engine + Docker Compose plugin and ports 80/443
open.

1. Clone the repo and copy the environment file:

   ```bash
   cp .env.example .env
   # edit .env
   ```

2. Required production variables:

   - `DOMAIN` — public domain pointed at the server (Caddy obtains HTTPS cert).
   - `DATABASE_URL` — `postgresql+asyncpg://mdr_user:mdr_pass@db:5432/mdr_db`
   - `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
   - `MAX_BOT_TOKEN`, `MAX_WEBHOOK_SECRET`, `MAX_GROUP_ID`
   - `BACKUP_DIR` — local directory for `pg_dump` (mounted into the DB container).
   - `SCHEDULER_TIMEZONE` — defaults to `Europe/Moscow`.

3. Start the stack:

   ```bash
   make prod-up
   ```

   This command:

   - starts PostgreSQL and waits until it is healthy,
   - runs `alembic upgrade head` in a one-off container,
   - starts `api`, `scheduler`, and `caddy`.

4. Caddy terminates HTTPS and reverse-proxies everything to the API container.
   The API serves the built React SPA from `/app/static`.

5. Register the MAX webhook:

   ```bash
   ./scripts/register_webhook.sh
   ```

   The script subscribes `https://${DOMAIN}/api/webhook/max` with the configured
   secret.

6. Seed catalogs and create group/private control panels via the admin endpoints
   or the existing UI.

## Scheduler

The `scheduler` container calls the scheduler HTTP endpoints at Moscow time:

- `00:05` — generate obligations for the new day.
- `20:00` — first evening reminder.
- `20:30` — second evening reminder.
- `08:00` — morning summary for the previous day.

Dry-run any job manually:

```bash
curl -X POST "https://${DOMAIN}/api/scheduler/morning"
curl -X POST "https://${DOMAIN}/api/scheduler/evening-reminder?group_id=1&reminder_number=1"
curl -X POST "https://${DOMAIN}/api/scheduler/morning-summary?group_id=1"
```

## Backups

```bash
make backup
```

Creates `BACKUP_DIR/mdr_YYYY-MM-DD_HH-MM-SS.sql` using `pg_dump` from the
running DB container.

## Useful commands

```bash
make prod-down     # stop production stack
make prod-logs     # tail logs
make migrate       # run migrations only
make backup        # manual backup
```
