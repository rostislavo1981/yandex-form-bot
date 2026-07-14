#!/bin/sh
set -e

cd "$(dirname "$0")/.."

docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head
