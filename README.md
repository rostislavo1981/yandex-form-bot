# Yandex Form Bot

> Этот README описывает существующий V1. Окончательное ТЗ нового MVP (Mini App, динамические справочники, группа MAX, табели по объектам, упрощённая админка `/admin/catalogs`) находится в [`docs/max-mini-app-spec/SUMMARY.md`](docs/max-mini-app-spec/SUMMARY.md). Рабочий код нового MVP — в `max_daily_report/`, его README и инструкции по запуску см. в [`max_daily_report/README.md`](max_daily_report/README.md).

MAX-бот + YandexGPT + Яндекс.Формы для ежедневных отчётов прорабов.

## Назначение

Прораб пишет в MAX свободным текстом отчёт. Бот:
1. Парсит текст через **YandexGPT** в JSON по 12 полям формы
2. Заполняет **Яндекс.Форму** через Playwright (headless Chromium)
3. Сохраняет JSON + скриншот на **Яндекс.Диск**
4. Пишет запись в **SQLite**
5. Отвечает в MAX: `✅ Отправлено 📅 2026-07-10 🏗 РП-7 📸 скриншот`
6. По команде `/webapp` показывает **Mini App** со сводной за период
7. По команде `/summary [дата]` шлёт **Excel**-файл

## Форма

Реальная форма (12 полей MVP, целевая — 142):

- **Дата отчёта** (date)
- **Прораб / Ответственный / Подрядчик** (foreman)
- **Объект** (object_name)
- **Комментарий** (comment)
- **Техника** (machine_type, unit, quantity) — список
- **Вывоз грунта, м³** (waste_volume)
- **ИТР** (itr)
- **ОПР (штатные)** (opr_staff)
- **ОПР (внештатные)** (opr_external)
- **Итоговый комментарий** (final_comment)
- (опц.) Погода

## Архитектура

```
┌──────────┐  текст    ┌─────────┐  JSON    ┌──────────────┐  скрин  ┌─────────────┐
│ Прораб   │──────────▶│ MAX Bot │──────────▶│ YandexGPT    │────────▶│ Playwright  │
│  (MAX)   │           │ (long   │  Report  │ (parser)     │  Report │ (Chromium)  │
└──────────┘           │ polling)│          └──────────────┘         └──────┬──────┘
                       └────┬────┘                                         │
                            │                                              ▼
                            │        ┌─────────────┐              ┌─────────────┐
                            ├───────▶│  SQLite     │              │ Yandex Disk │
                            │        │ (app.db)    │              │ (JSON+PNG)  │
                            │        └─────────────┘              └─────────────┘
                            │
                            ▼
                       ┌──────────┐
                       │ FastAPI  │ ← HMAC-аутентификация
                       │  /api/*  │   (MAX initData)
                       └────┬─────┘
                            │
                            ▼
                       ┌──────────┐
                       │ Mini App │ ← webview внутри MAX
                       │ (HTML+JS)│
                       └──────────┘
```

## Команды бота

| Команда | Что делает |
|---|---|
| `/help` | Список команд |
| `/webapp` | Открывает Mini App с карточками отчётов |
| `/summary [YYYY-MM-DD]` | Excel-сводная за день (default: вчера) |
| любой текст | Отчёт прораба → парсится → форма → диск → БД |

## Быстрый старт

```bash
# 1. Установить
git clone https://github.com/rostislavo1981/yandex-form-bot.git
cd yandex-form-bot
make install       # uv/venv + pip install -e ".[dev]"
playwright install chromium   # только если заполнять реальную форму

# 2. Настроить
cp .env.example .env
# Заполнить MAX_BOT_TOKEN, YANDEX_GPT_API_KEY, YANDEX_GPT_FOLDER_ID,
# FORM_PUBLISHED_URL, YANDEX_DISK_OAUTH_TOKEN, WEBAPP_PUBLIC_URL

# 3. Запустить
make bot          # MAX-бот (long polling)
make api          # FastAPI (Mini App backend) на :8000
# или
make test         # pytest
make lint         # ruff
```

## Деплой

### Локально (Mac)
```bash
INSTALL_PLAYWRIGHT=1 docker compose up -d bot
```

### На сервере (Linux)
```bash
sudo ./deploy/install.sh
# → /opt/yandex-form-bot, systemd unit, автозапуск
```

За reverse-proxy (nginx/Caddy) для HTTPS обязательно — MAX WebApp требует HTTPS.

## Тесты

```bash
make test    # 152 теста, все зелёные
make lint    # ruff clean
```

E2E smoke (проверяет pipeline → DB → API → Mini App JSON):
```bash
.venv/bin/python -c "import asyncio; from backend.forms import FakePlaywrightClient; ..."
```

## Документация

- `docs/max-mini-app-spec/SUMMARY.md` — окончательное ТЗ нового MVP (Mini App-first)
- `docs/max-mini-app-spec/04_api_contract.md` — актуальный REST-контракт, включая `/api/admin/catalogs`
- `docs/api.md` — архивный REST API V1
- `docs/architecture.md` — архивная архитектура V1
- `docs/deploy.md` — архивный деплой V1 (новый MVP — `max_daily_report/README.md`)
- `docs/roadmap.md` — исторический roadmap V1

## Стек

- Python 3.12+ / FastAPI / Pydantic v2 / httpx
- YandexGPT (lite-модель для экономии)
- Playwright (sync → asyncio.to_thread)
- SQLite (встроено)
- openpyxl (Excel)
- pytest + ruff (тесты и линтер)
- Docker + systemd (деплой)

## Лицензия

MIT
