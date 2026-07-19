#!/bin/sh
set -eu

cd "$(dirname "$0")/.."

set -a
# shellcheck source=/dev/null
. ./.env.phone
set +a

missing=""
for name in MAX_BOT_TOKEN MAX_WEBHOOK_SECRET INTERNAL_TOKEN; do
    eval "value=\${$name:-}"
    if [ -z "$value" ]; then
        missing="$missing $name"
    fi
done

if [ -n "$missing" ]; then
    echo "ERROR: fill these values in .env.phone:$missing" >&2
    exit 1
fi

docker compose -f docker-compose.phone.yml up -d --build \
    db migrations api worker scheduler tunnel

# Quick Tunnel hostnames are disposable.  Always request a fresh hostname so
# an apparently running container cannot leave the bot pointed at expired DNS.
docker compose -f docker-compose.phone.yml up -d --force-recreate tunnel

check_public_ready() {
    if curl -fsS --connect-timeout 3 --max-time 8 \
        "$public_url/api/ready" >/dev/null 2>&1; then
        return 0
    fi

    # macOS can keep NXDOMAIN in its local cache just after Cloudflare creates
    # the hostname.  Verify the same HTTPS endpoint through a public resolver
    # before discarding an otherwise healthy tunnel.
    if ! command -v dig >/dev/null 2>&1; then
        return 1
    fi
    public_host="${public_url#https://}"
    public_host="${public_host%%/*}"
    public_ip="$(
        dig +short "$public_host" @1.1.1.1 2>/dev/null \
            | sed -n '/^[0-9.][0-9.]*$/p' \
            | head -n 1
    )"
    [ -n "$public_ip" ] || return 1
    curl -fsS --connect-timeout 3 --max-time 8 \
        --resolve "${public_host}:443:${public_ip}" \
        "$public_url/api/ready" >/dev/null 2>&1
}

wait_for_tunnel() {
    public_url=""
    attempt=0
    while [ "$attempt" -lt 30 ]; do
        public_url="$(
            docker compose -f docker-compose.phone.yml logs --no-color tunnel 2>/dev/null \
                | sed -n 's#.*\(https://[a-zA-Z0-9-]*\.trycloudflare\.com\).*#\1#p' \
                | tail -n 1
        )"
        if [ -n "$public_url" ] && check_public_ready; then
            return 0
        fi
        public_url=""
        attempt=$((attempt + 1))
        sleep 2
    done
    return 1
}

tunnel_round=1
while ! wait_for_tunnel; do
    if [ "$tunnel_round" -ge 3 ]; then
        break
    fi
    echo "Tunnel hostname is not reachable; requesting a new one..." >&2
    docker compose -f docker-compose.phone.yml up -d --force-recreate tunnel
    tunnel_round=$((tunnel_round + 1))
done

if [ -z "$public_url" ]; then
    echo "ERROR: Cloudflare Quick Tunnel did not become ready" >&2
    docker compose -f docker-compose.phone.yml logs --tail=30 tunnel >&2
    exit 1
fi

docker compose -f docker-compose.phone.yml run --rm \
    -e "WEBAPP_PUBLIC_URL=$public_url" \
    api python -m app.register_webhook

webhook_url="${public_url%/}/api/webhook/max"
echo "Phone test is active."
echo "Mini App URL: $public_url"
echo "Webhook URL:  $webhook_url"
echo "Set this Mini App URL in the MAX partner cabinet while this stand is running."
