# Deploy

## Вариант 1: Docker (рекомендуется)

### Локально (Mac)

```bash
# 1. Подготовить .env
cp .env.example .env
# Заполнить MAX_BOT_TOKEN, YANDEX_GPT_API_KEY, YANDEX_GPT_FOLDER_ID,
# FORM_PUBLISHED_URL, YANDEX_DISK_OAUTH_TOKEN

# 2. Запустить бота + API
INSTALL_PLAYWRIGHT=1 docker compose up -d

# Логи
docker compose logs -f bot
docker compose logs -f api   # только если запущен с --profile api

# 4. Открыть API (Mini App)
open http://localhost:8000/docs
```

### VPS (Ubuntu/Debian)

```bash
# 1. Скопировать .env на сервер
scp .env user@server:/opt/yandex-form-bot/

# 2. Запустить
ssh user@server "cd /opt/yandex-form-bot && \
  INSTALL_PLAYWRIGHT=1 docker compose up -d"
```

### HTTPS (обязательно для MAX WebApp)

MAX Mini App требует HTTPS. Варианты:

**Cloudflare Tunnel (проще всего):**
```bash
cloudflared tunnel create yfb
cloudflared tunnel route dns yfb bot.example.com
cloudflared tunnel run yfb   # или как сервис
```

**Caddy (reverse-proxy + авто-LE):**
```caddyfile
bot.example.com {
    reverse_proxy 127.0.0.1:8000
}
```

**nginx + certbot:**
```nginx
server {
    server_name bot.example.com;
    listen 443 ssl http2;
    ssl_certificate /etc/letsencrypt/live/bot.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bot.example.com/privkey.pem;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    location /miniapp/ {
        alias /opt/yandex-form-bot/miniapp/;
        expires 1h;
    }
}
```

## Вариант 2: systemd (без Docker)

```bash
sudo ./deploy/install.sh
# → /opt/yandex-form-bot, venv, systemd unit, env file
sudo systemctl status yandex-form-bot
sudo journalctl -u yandex-form-bot -f
```

## Вариант 3: Development

```bash
# Терминал 1: бот
make bot

# Терминал 2: API (Mini App)
make api
# FastAPI on http://localhost:8000
# Mini App: http://localhost:8000/miniapp/index.html

# Терминал 3: тесты
make test
```

## Что нужно в .env

| Переменная | Где взять |
|---|---|
| `MAX_BOT_TOKEN` | BotFather в MAX |
| `YANDEX_GPT_API_KEY` | https://console.yandex.cloud (сервисный аккаунт) |
| `YANDEX_GPT_FOLDER_ID` | Там же, ID каталога |
| `YANDEX_DISK_OAUTH_TOKEN` | OAuth-приложение Яндекс.Диска |
| `FORM_PUBLISHED_URL` | После публикации формы на forms.yandex.ru |
| `WEBAPP_PUBLIC_URL` | Ваш домен, например https://bot.example.com |

## Размер образа

| Сборка | Размер |
|---|---|
| `INSTALL_PLAYWRIGHT=0` (только бот) | ~400 MB (без Chromium) |
| `INSTALL_PLAYWRIGHT=1` (с Chromium) | ~700 MB |

## Проверка

```bash
# Бот жив?
curl http://localhost:8000/healthz
# {"ok":true,"version":"0.1.0"}

# API жив?
curl -H "X-Auth-InitData: ..." \
  "http://localhost:8000/api/summary?date_from=2026-07-10&date_to=2026-07-10"
```

## Обновление

```bash
git pull
docker compose build
docker compose up -d
```
