# 02. Архитектура

## Компоненты

```
┌──────────────────┐
│  Прораб в MAX    │  (Android/iOS/web клиент MAX)
└────────┬─────────┘
         │  сообщения / нажатия кнопок / открытие webview
         ▼
┌────────────────────────────────────────────────────────────────┐
│                   MAX Bot API (внешний)                        │
│   - long polling: bot получает updates                         │
│   - sendMessage / answerCallbackQuery / editMessageReplyMarkup │
└────────┬───────────────────────────────────────▲───────────────┘
         │ updates                                │ replies
         ▼                                        │
┌──────────────────┐                    ┌─────────┴──────────┐
│  bot worker      │                    │  bot worker (out)  │
│  (Python async)  │                    │                    │
└────────┬─────────┘                    └────────▲───────────┘
         │ вызовы                                │
         ▼                                        │
┌────────────────────────────────────────────────────────────────┐
│                 FastAPI backend  (порт 8000)                   │
│                                                                │
│  /api/health          — liveness                               │
│  /api/bootstrap       — справочники                            │
│  /api/reports         — POST/GET                               │
│  /api/reports/{id}    — GET                                    │
│  /api/summary         — агрегаты за период                     │
│  /api/export.xlsx     — выгрузка                               │
│                                                                │
│  middleware:                                                   │
│   - CORS (только домен Mini App)                               │
│   - HMAC verify initData (X-Auth-InitData header)              │
└────────┬───────────────────────────────────────────────────────┘
         │ SQLAlchemy 2.0 (async)
         ▼
┌──────────────────┐
│  PostgreSQL 16   │
└──────────────────┘

┌────────────────────────────────────────────────────────────────┐
│  Frontend Mini App  (React/Vite, статика)                      │
│  - / (форма отчёта)                                            │
│  - /summary (сводная)                                          │
│  Раздаётся через nginx/Caddy на HTTPS-домене                   │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│  Gateway (Caddy или nginx)                                     │
│  - :443 → HTTPS (Let's Encrypt автоматически у Caddy)           │
│  - /api/* → backend:8000                                       │
│  - /*     → frontend (статика)                                 │
└────────────────────────────────────────────────────────────────┘
```

## Процессы

| Процесс | Как запускается | Что делает |
|---|---|---|
| `db` | контейнер | PostgreSQL |
| `backend` | контейнер, `uvicorn app.main:app` | REST API |
| `bot` | контейнер, `python -m app.bot` | long polling к MAX, вызывает backend |
| `frontend` | контейнер (build → статика) | отдаёт SPA |
| `gateway` | контейнер (Caddy/nginx) | HTTPS + маршрутизация |

`bot` и `backend` — **два отдельных процесса** одного Python-проекта. Bot ходит в backend по HTTP (внутри compose-сети). Так проще масштабировать и перезапускать бот, не трогая API.

## Поток: создание отчёта

```
1. Прораб: жмёт «Открыть форму» в чате
2. MAX клиент: запускает webview с URL Mini App + initData
3. Mini App: GET /api/bootstrap  (заголовок X-Auth-InitData)
4. Backend: verify HMAC → 200 + справочники
5. Mini App: рендерит форму
6. Прораб: заполняет и жмёт «Отправить»
7. Mini App: POST /api/reports  (заголовок X-Auth-InitData)
8. Backend: verify HMAC → валидация → INSERT → 200 {id}
9. Mini App: показывает «✅ Отправлено», через 2 сек закрывается
10. Backend: (опционально) шлёт боту сигнал → бот пишет прорабу подтверждение
```

Пункт 10 — **не обязателен для MVP**: Mini App сам показывает успех. Если нужно продублировать в чат, backend делает `POST bot-service:/notify` с текстом.

## Поток: авторизация

MAX при открытии Mini App кладёт в `window.MaxApp.initData` (или аналог — уточнить по документации) подписанную строку с полями `user_id`, `auth_date`, `hash`. Mini App шлёт её в каждом запросе в заголовке `X-Auth-InitData`.

Backend в middleware:
1. Парсит query-string формат.
2. Считает `secret = SHA256(bot_token)`.
3. Считает `expected = HMAC_SHA256(secret, data_check_string)`.
4. Сравнивает через `hmac.compare_digest` с полем `hash`.
5. Проверяет `auth_date` не старше 24 часов.
6. Кладёт `max_user_id` в `request.state.user_id`.

Если проверка провалилась → `401`.

> **[непроверено]** Точное имя JS-объекта (`MaxApp`/`Max`/`MAX`) и формат `initData` берётся из актуальной документации MAX перед реализацией. Формат HMAC описан по аналогии с Telegram WebApp — уточнить, что MAX использует ту же схему; если нет — переписать `webapp_auth.py`.

## Деплой

### Локально (Mac/Linux)
```
docker compose up --build
```
- Порт 8080 → Caddy → frontend + backend.
- Bot стартует, но `MAX_BOT_TOKEN` может быть заглушкой (в dev-режиме бот пишет в лог, а не в MAX).
- HTTPS локально не нужен — MAX открывать не будем, тестируем формой в браузере.

### VPS (production)
1. Домен + A-запись на IP сервера.
2. `docker compose -f docker-compose.prod.yml up -d`.
3. Caddy автоматически берёт Let's Encrypt сертификат.
4. В BotFather MAX регистрируем URL Mini App: `https://<domain>/`.

## Технологические решения

| Решение | Почему |
|---|---|
| Python 3.12 + FastAPI | Один язык на bot + api, быстрый старт, знакомый стек |
| PostgreSQL 16 | Нормализованная схема, UNIQUE constraints, native JSONB на будущее |
| SQLAlchemy 2.0 async | Единый стиль, миграции через Alembic |
| React + Vite + TypeScript | Быстрый dev, типы для API |
| httpx | Async HTTP клиент (bot → MAX API, bot → backend) |
| Caddy | Автоматический HTTPS, минимум конфига |
| Docker Compose | Единая команда запуска |

## Что откладываем

- **Alembic-миграции**: в MVP `Base.metadata.create_all()` на старте. Alembic — Phase 5.
- **Redis/очереди**: bot синхронный, поллинг простой.
- **Sentry/логи в облако**: stdout + docker logs.
- **Тесты в CI**: локально `pytest`; GitHub Actions — Phase 6.
