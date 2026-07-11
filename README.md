# Yandex Form Bot

MAX-бот + YandexGPT + Яндекс Формы для ежедневных отчётов прорабов.

## Назначение

Прораб пишет в MAX свободным текстом отчёт о выполненных работах. Бот:
1. Парсит текст через **YandexGPT** в структурированный `Report` (JSON)
2. Заполняет **Яндекс Форму** (через Playwright headless Chromium)
3. Сохраняет JSON + скриншот на **Яндекс Диск** (накопительно)
4. Записывает в локальный **SQLite**
5. По команде `/summary [YYYY-MM-DD]` присылает в MAX **Excel-сводную** за день

## Структура

```
yandex-form-bot/
├── backend/
│   ├── app.py               # FastAPI /healthz
│   ├── config.py            # pydantic Settings
│   ├── schemas.py           # Report / WorkItem / Material
│   ├── llm/                 # YandexGPT client + parser + system prompt
│   ├── forms/               # Playwright filler + MVP field map + real client
│   ├── disk/                # Yandex Disk REST client + archive_report
│   ├── db/                  # SQLite DAO
│   ├── excel/               # build_summary + safe_str/safe_float
│   ├── pipeline.py          # end-to-end orchestrator
│   ├── max/                 # MaxClient (Telegram-compatible) + polling bot
│   └── cli/                 # yfb-parse / yfb-fill / yfb-pipeline / yfb-bot / yfb-api
├── tests/                   # 123 passed, ruff clean
├── scripts/                 # golden regen
├── deploy/                  # systemd unit + install.sh
├── Dockerfile               # python:3.12-slim, optional Playwright
├── docker-compose.yml       # bot (always) + api (profile)
├── Makefile                 # install/lint/test/api/bot/clean
├── pyproject.toml           # deps + ruff + pytest
└── .env.example
```

## Quickstart (dev)

```bash
make install          # .venv + editable install
cp .env.example .env  # fill in YANDEX_GPT_API_KEY, MAX_BOT_TOKEN, FORM_PUBLISHED_URL
make test             # 123 passed
```

## Quickstart (prod, Docker)

```bash
cp .env.example .env  # fill in
# Build (default: no Chromium; small image)
docker compose build
docker compose up -d bot reminder
docker compose logs -f bot reminder

# Enable debug API on localhost:8000:
docker compose --profile api up -d api
curl http://127.0.0.1:8000/healthz

# Include Chromium (~300MB more) for real Yandex Forms filling:
# INSTALL_PLAYWRIGHT=1 docker compose build
```

The `reminder` service runs an in-process scheduler that fires
`yfb-reminder` at `REMINDER_HOUR:REMINDER_MINUTE` (default 20:00) every day
in the timezone from `TZ` (default `Europe/Moscow`). No system cron needed.

## Quickstart (RPi / systemd)

```bash
# on the Pi, as root
git clone <repo> /opt/yandex-form-bot
cd /opt/yandex-form-bot
INSTALL_PLAYWRIGHT=1 sudo ./deploy/install.sh
sudo vi /opt/yandex-form-bot/.env    # fill secrets
sudo systemctl restart yandex-form-bot
journalctl -u yandex-form-bot -f
```

## CLI

```bash
# Parse a foreman report into Report JSON (no form filling, no disk)
.venv/bin/yfb-parse tests/fixtures/reports/foreman_stepanov_2026-07-10.txt

# Run full pipeline on a text file
.venv/bin/yfb-pipeline tests/fixtures/reports/foreman_stepanov_2026-07-10.txt --fake-form

# Start the bot (long polling, blocks)
.venv/bin/yfb-bot
```

## MAX bot commands

| Команда | Что делает |
|---|---|
| `/help` | Помощь |
|| `/start` | Подписаться на напоминание в 20:00 |
|| `/stop` | Отписаться от напоминаний |
|| `/summary` | Excel за **вчера** |
|| `/summary 2026-07-10` | Excel за конкретный день |
|| любой текст | Парсится как отчёт прораба → форма + диск + БД |

## Напоминания

Два пути:

1. **Docker (рекомендуется для prod):** поднимаешь `reminder` сервис через
   `docker compose up -d reminder`. Внутри контейнера крутится
   `backend/cli/scheduler.py`, который спит до 20:00 (или `REMINDER_HOUR:MINUTE`)
   и вызывает `yfb-reminder`. Работает 24/7 пока жив контейнер.

2. **Hermes cron (только для dev на Mac):** задача `4dbfe8c2d2a2`
   в `cronjob`. Работает только пока запущен Hermes и Mac не спит.

Подписчики хранятся в `data/subscribers.json` (формируется через `/start` в боте).

## Разработка

- **TDD:** все стадии — с тестами (parser, disk, forms, db, excel, bot, max, pipeline).
- **Golden tests:** `tests/filler_golden` фиксирует последовательность заполнения формы. Регенерация: `python scripts/_gen_golden_fill_sequences.py`.
- **Lint:** `make lint` (ruff).
- **Str(config):** в проде `STRICT_CONFIG=1` (docker-compose по умолчанию) — бот не стартует без секретов.
- **Данные в репо не попадают:** `data/` gitignored. SQLite, скриншоты, кэш Chromium — всё в `data/`.

## Связанные артефакты

- **Форма:** https://forms.yandex.ru/admin/6a51e57af47e73a0eca7b48c/edit
- **ID:** `6a51e57af47e73a0eca7b48c`
- **Текущих вопросов:** 7 (нужно доделать до 142)
- **Скоуп MVP:** 10 полей формы, 1 прораб (DEFAULT_FOREMAN=Степанов), 1 объект.

## Что нужно от пользователя

| Что | Где |
|---|---|
| YandexGPT API key | https://yandex.cloud |
| MAX-бот токен | @MasterBot в MAX |
| OAuth Яндекс Диска | https://oauth.yandex.ru |
| ID опубликованной формы | будет после публикации |
