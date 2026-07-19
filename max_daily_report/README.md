# MAX Daily Report

FastAPI backend + Vite React frontend for daily construction reports inside the
[MAX](https://max.ru) messenger.

## Local development

```bash
make install       # create venv, install deps, copy .env.example to .env
make db-up         # start PostgreSQL in Docker
make test          # pytest (uses mdr_test database)
make lint          # ruff
make api           # uvicorn --reload on :8000
make frontend-check # build + vitest
```

Fill `.env` with `MAX_BOT_TOKEN`, `MAX_BOT_USERNAME`, `MAX_WEBHOOK_SECRET`,
`MAX_GROUP_ID` before using real MAX features. Dev mode is gated **strictly
on `APP_ENV=dev`** (setting `DEBUG=true` alone does NOT bypass auth): it
auto-creates a placeholder user and accepts the `dev` initData fallback so
you can test the Mini App in a browser at `http://127.0.0.1:8080/` without
launching it from MAX.

In production every `/api/*` endpoint requires a valid `X-Init-Data` header
(validated against `MAX_BOT_TOKEN`); `/api/scheduler/*` and
`/api/worker/*` are internal and require `X-Internal-Token` equal to
`INTERNAL_TOKEN` from `.env`.

## Test from a phone through MAX

This stand is isolated from the regular local database and exposes the Mini App
through a temporary HTTPS Cloudflare Quick Tunnel.

```bash
cp .env.phone.example .env.phone
# put MAX_BOT_TOKEN into .env.phone; never paste it into a chat or commit it
./scripts/activate_phone_test.sh
```

The activation script builds the stand, runs migrations, waits for a generated
`https://...trycloudflare.com` address, checks `/api/ready`, and registers that
address as the only current webhook: subscriptions for previous tunnel URLs are
removed automatically. Set the printed address as the Mini App URL in the MAX
partner cabinet. A Quick Tunnel is ephemeral and may expire even while its
container is still shown as running; rerun the activation script immediately
before a phone test and use the newly printed URL. Seed demo catalogs only when
you need them:

```bash
docker compose -f docker-compose.phone.yml run --rm api python -m app.seed
```

To import a real workbook without opening the admin screen, mount it read-only
and run the same validator/applier used by the API:

```bash
docker compose -f docker-compose.phone.yml run --rm \
  -v "/absolute/path/objects.xlsx:/imports/objects.xlsx:ro" \
  api python -m app.import_catalog_file /imports/objects.xlsx
```

A simple workbook with the `краткое название` column imports short object names
and their detailed contract names. Every imported active object is linked to
all active stages already stored in PostgreSQL; the import is rejected when no
active stage exists. The simple file has no MAX user IDs, so responsible users
and object assignments must be added through the admin screen or the full
`Users`/`Assignments` Excel template.

Add the bot to the test group as an administrator. If `MAX_GROUP_ID` is set,
rerun `python -m app.seed`; the seed then creates/activates that real group and
disables the placeholder group. The quick-tunnel address remains valid only
while `mdr-phone-tunnel` is running. Stop the stand without deleting its data:

```bash
docker compose -f docker-compose.phone.yml down
```

The Docker image installs the current Russian Trusted Root/Sub CA certificates
published through the Госуслуги certificate page. MAX API currently uses this
chain; TLS verification remains enabled.

The dev placeholder user is `dev-user` (role `responsible` until you run
`python -m app.seed`, which creates `dev-user` with the `admin` role). In dev
mode open `/admin/catalogs` to manage catalogs.

## Production deploy

Target: a clean VPS with Docker Engine + Docker Compose plugin and ports 80/443
open.

1. Clone the repo and copy the environment file:

   ```bash
   cp .env.example .env
   # edit .env
   ```

   For local Docker testing change `DATABASE_URL` host from `db` to
   `localhost` and use `make db-up` / `make db-down`. For real production
   set it back to `db` so containers can resolve each other.

2. Required production variables:

   - `DOMAIN` — public domain pointed at the server; Caddy obtains a
     Let's Encrypt certificate automatically (HTTPS is mandatory for the MAX
     Mini App). Leave `:80` for plain-HTTP local smoke testing.
   - `DATABASE_URL` — `postgresql+asyncpg://mdr_user:mdr_pass@db:5432/mdr_db`
   - `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
   - `MAX_BOT_TOKEN`, `MAX_BOT_USERNAME`, `MAX_WEBHOOK_SECRET`, `MAX_GROUP_ID`
   - `WEBAPP_PUBLIC_URL` — fallback Mini App link when the bot username is unset.
   - `INTERNAL_TOKEN` — shared secret for `/api/scheduler/*` and
     `/api/worker/*` (required in production; empty allows dev-only access).
   - `BACKUP_DIR` — local directory for `pg_dump` (mounted into the DB container).
   - `SCHEDULER_TIMEZONE` — defaults to `Europe/Moscow`.

3. Start the stack:

   ```bash
   make prod-up
   ```

   This command:

   - starts PostgreSQL and waits until it is healthy,
   - runs `alembic upgrade head` in a one-off container,
   - starts `api`, separate outbox `worker`, `scheduler`, daily `backup`, and
     `caddy`.

4. Caddy terminates HTTPS and reverse-proxies everything to the API container.
   The API serves the built React SPA from `/app/static`.

5. Register the MAX webhook:

   ```bash
   ./scripts/register_webhook.sh
   ```

   The script subscribes `https://${DOMAIN}/api/webhook/max` with the configured
   secret and removes subscriptions for obsolete URLs.

6. Seed catalogs and assignments:

   ```bash
   docker exec -e PYTHONPATH=/app mdr-api python -m app.seed
   ```

   Seed creates two responsible users (`max-resp-1`, `max-resp-2`), a manager
   (`max-manager-1`), a dev admin (`dev-user`), two objects (`obj-1`, `obj-2`)
   and assigns each responsible to one object with a daily schedule.

7. Open the admin page at `/admin/catalogs` (only managers/admins) to edit
   objects, stages, contractors, units, equipment, work types, methods,
   object-stage links, work-type-method links, responsible assignments and
   users. Use the **Export Excel** / **Import** buttons to bulk-edit catalogs.

## Connecting to real MAX

1. **Create a MAX bot** and get a bot token from the MAX partner cabinet.
2. **Create a MAX group/chat** for your construction team and add the bot as an
   **administrator** with the right to pin messages.
3. Copy the group/chat ID into `.env` as `MAX_GROUP_ID`.
4. Set `MAX_WEBHOOK_SECRET` to a long random string.
5. Deploy the application on a VPS with a public domain and HTTPS (Caddy does
   this automatically when `DOMAIN` is set and DNS points to the server).
6. Register the webhook:

   ```bash
   ./scripts/register_webhook.sh
   ```

   This tells MAX to deliver updates to `https://${DOMAIN}/api/webhook/max`.

7. The bot receives `bot_added`, `bot_removed`, `bot_started` and
   `message_callback` events. Users are auto-created in the DB from MAX IDs;
   the admin assigns them to objects on `/admin/catalogs` or through the full
   Users/Assignments Excel workbook.
8. Send `/start` or open the Mini App from the group control panel to begin.

### What each MAX event does

- `bot_started` — creates/updates the user and sends a personal control panel.
- `bot_added` — activates the group, records the initiating user and creates
  the visible group control panel.
- `bot_removed` — deactivates the group.
- `message_callback` — handles buttons: open app, status, timesheet, Excel.
- `open_app` (Mini App launch) — frontend sends `initData` in the
  `X-Init-Data` header; the backend validates it and resolves the user.

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

Creates `BACKUP_DIR/mdr_YYYY-MM-DD_HH-MM-SS.dump` using `pg_dump -Fc` from the
running DB container. Production Compose also creates a backup every 24 hours
and removes files older than `BACKUP_RETENTION_DAYS`.

Verify that the newest dump can be restored into an isolated temporary DB:

```bash
make restore-smoke
```

## Useful commands

```bash
make prod-down     # stop production stack
make prod-logs     # tail logs
make migrate       # run migrations only
make backup        # manual backup
make restore-smoke # verify newest backup in a temporary DB
```
