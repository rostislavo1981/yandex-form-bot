#!/bin/sh
set -eu

cd "$(dirname "$0")/.."

BACKUP_DIR="${BACKUP_DIR:-./backups}"
USER="${POSTGRES_USER:-mdr_user}"
RESTORE_DB="${RESTORE_TEST_DB:-mdr_restore_test}"

LATEST="$(find "$BACKUP_DIR" -type f -name 'mdr_*.dump' -print | sort | tail -n 1)"
if [ -z "$LATEST" ]; then
    echo "ERROR: no .dump backup found in $BACKUP_DIR" >&2
    exit 1
fi

docker exec mdr-db dropdb -U "$USER" --if-exists "$RESTORE_DB"
docker exec mdr-db createdb -U "$USER" "$RESTORE_DB"
docker exec -i mdr-db pg_restore -U "$USER" -d "$RESTORE_DB" < "$LATEST"
docker exec mdr-db psql -U "$USER" -d "$RESTORE_DB" -v ON_ERROR_STOP=1 -c "SELECT 1" >/dev/null
docker exec mdr-db dropdb -U "$USER" "$RESTORE_DB"

echo "Restore smoke passed: $LATEST"
