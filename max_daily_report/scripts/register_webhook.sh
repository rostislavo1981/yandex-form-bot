#!/bin/sh
set -e

cd "$(dirname "$0")/.."

# shellcheck source=/dev/null
. ./.env

DOMAIN="${DOMAIN:-localhost}"
URL="https://${DOMAIN}/api/webhook/max"

if [ -z "$MAX_BOT_TOKEN" ] || [ -z "$MAX_WEBHOOK_SECRET" ]; then
    echo "MAX_BOT_TOKEN and MAX_WEBHOOK_SECRET must be set in .env"
    exit 1
fi

curl -fsS -X POST "https://platform-api2.max.ru/subscriptions" \
    -H "Authorization: $MAX_BOT_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"url\":\"$URL\",\"secret\":\"$MAX_WEBHOOK_SECRET\"}"
