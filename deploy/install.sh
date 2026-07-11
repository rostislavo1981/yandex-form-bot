#!/usr/bin/env bash
# Install yfb on a fresh RPi (or any systemd Linux).
# Usage: sudo ./deploy/install.sh
set -euo pipefail

REPO_DIR="/opt/yandex-form-bot"
SERVICE_USER="yfb"

if [ "$(id -u)" -ne 0 ]; then
    echo "must be root" >&2
    exit 1
fi

# 1. Create user
if ! id "$SERVICE_USER" >/dev/null 2>&1; then
    useradd --system --shell /bin/bash --home-dir "$REPO_DIR" --create-home "$SERVICE_USER"
fi

# 2. Sync code (assumes you've already copied/checked-out the repo)
mkdir -p "$REPO_DIR"
rsync -a --delete \
    --exclude '.git' --exclude '.venv' --exclude '__pycache__' \
    --exclude 'data' --exclude '.env' --exclude '*.egg-info' \
    ./ "$REPO_DIR/"

# 3. venv + deps
cd "$REPO_DIR"
[ -d .venv ] || python3 -m venv .venv
chown -R "$SERVICE_USER:$SERVICE_USER" .venv
sudo -u "$SERVICE_USER" .venv/bin/pip install --upgrade pip
sudo -u "$SERVICE_USER" .venv/bin/pip install -e ".[bot,playwright]"

# 4. Playwright browser (only if user wants real form filling)
if [ "${INSTALL_PLAYWRIGHT:-0}" = "1" ]; then
    sudo -u "$SERVICE_USER" .venv/bin/playwright install --with-deps chromium
fi

# 5. .env (interactive, only if missing)
if [ ! -f .env ]; then
    echo "=== Creating .env — fill in your secrets ==="
    cp .env.example .env
    chown "$SERVICE_USER:$SERVICE_USER" .env
    chmod 600 .env
    echo "Edit $REPO_DIR/.env and rerun: sudo systemctl start yandex-form-bot"
    exit 0
fi

# 6. systemd unit
install -m 644 deploy/yandex-form-bot.service /etc/systemd/system/yandex-form-bot.service
systemctl daemon-reload
systemctl enable yandex-form-bot
systemctl restart yandex-form-bot

echo "=== Installed. Status: ==="
systemctl status yandex-form-bot --no-pager
