#!/bin/sh
set -e

cd "$(dirname "$0")/.."

BACKUP_DIR="${BACKUP_DIR:-./backups}"
USER="${POSTGRES_USER:-mdr_user}"
DB="${POSTGRES_DB:-mdr_db}"
DUMP_FILE="${BACKUP_DIR}/mdr_$(date +%F_%H-%M-%S).sql"

mkdir -p "$BACKUP_DIR"
docker exec mdr-db pg_dump -U "$USER" -d "$DB" > "$DUMP_FILE"

echo "Backup saved to $DUMP_FILE"
