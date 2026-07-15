#!/bin/sh
set -e

cd "$(dirname "$0")/.."

# shellcheck source=/dev/null
. ./.env

DOMAIN="${DOMAIN:-localhost}"
INTERNAL_TOKEN="${INTERNAL_TOKEN:-}"

preflight() {
    errors=0
    if [ -z "$MAX_BOT_TOKEN" ]; then
        echo "ERROR: MAX_BOT_TOKEN is not set"
        errors=$((errors + 1))
    fi
    if [ -z "$MAX_WEBHOOK_SECRET" ]; then
        echo "ERROR: MAX_WEBHOOK_SECRET is not set"
        errors=$((errors + 1))
    fi
    if [ -z "$INTERNAL_TOKEN" ]; then
        echo "ERROR: INTERNAL_TOKEN is not set (required for production)"
        errors=$((errors + 1))
    fi
    case "$DOMAIN" in
        ""|":80"|localhost*)
            if [ "$APP_ENV" = "production" ]; then
                echo "ERROR: DOMAIN must be a real domain for production, got: $DOMAIN"
                errors=$((errors + 1))
            fi
            ;;
    esac
    if [ "$errors" -gt 0 ]; then
        echo "Preflight failed with $errors error(s)"
        exit 1
    fi
    echo "Preflight passed"
}

preflight

if echo "$DOMAIN" | grep -qE '^(:80|localhost)'; then
    URL="http://${DOMAIN}/api/webhook/max"
else
    URL="https://${DOMAIN}/api/webhook/max"
fi

echo "Registering webhook: $URL"

curl -fsS -X POST "https://platform-api2.max.ru/subscriptions" \
    -H "Authorization: $MAX_BOT_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"url\":\"$URL\",\"secret\":\"$MAX_WEBHOOK_SECRET\",\"update_types\":[\"bot_started\",\"message_callback\"]}"

echo ""
echo "Webhook registered successfully"
