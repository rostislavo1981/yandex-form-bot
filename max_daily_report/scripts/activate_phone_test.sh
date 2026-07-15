#!/bin/sh
set -eu

cd "$(dirname "$0")/.."

set -a
# shellcheck source=/dev/null
. ./.env.phone
set +a

missing=""
for name in MAX_BOT_TOKEN MAX_WEBHOOK_SECRET INTERNAL_TOKEN WEBAPP_PUBLIC_URL; do
    eval "value=\${$name:-}"
    if [ -z "$value" ]; then
        missing="$missing $name"
    fi
done

if [ -n "$missing" ]; then
    echo "ERROR: fill these values in .env.phone:$missing" >&2
    exit 1
fi

case "$WEBAPP_PUBLIC_URL" in
    https://*) ;;
    *)
        echo "ERROR: WEBAPP_PUBLIC_URL must start with https://" >&2
        exit 1
        ;;
esac

docker compose -f docker-compose.phone.yml up -d --force-recreate api worker scheduler

docker compose -f docker-compose.phone.yml run --rm api python -m app.register_webhook

webhook_url="${WEBAPP_PUBLIC_URL%/}/api/webhook/max"
echo "Phone test is active."
echo "Mini App URL: $WEBAPP_PUBLIC_URL"
echo "Webhook URL:  $webhook_url"
