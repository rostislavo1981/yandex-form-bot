# 02. Архитектура MVP

## Компоненты

```text
MAX group / private bot
  ├─ inline-кнопки
  ├─ краткие отчёты
  ├─ напоминания
  └─ утренняя сводка
             │ Bot API / webhook
             ▼
┌─────────────────────────────────────┐
│ FastAPI app                         │
│ /api/health                         │
│ /api/auth/me                        │
│ /api/webhook/max                    │
│ /api/catalogs/*                     │
│ /api/admin/catalogs/*               │
│ /api/reports, /api/submission-status│
│ /api/timesheet/*                    │
│ /api/control-panel/*                │
│ /api/scheduler/*                    │
│ /api/worker/process-outbox          │
│ /api/catalogs/{import,export}.xlsx  │
│ собранная статика Mini App          │
└────────────────┬────────────────────┘
                 │ SQLAlchemy async
                 ▼
          PostgreSQL 16
                 ▲
                 │
┌────────────────┴────────────────────┐
│ scheduler (тот же Python image)     │
│ obligations / reminders / morning  │
└─────────────────────────────────────┘

Caddy: HTTPS и reverse proxy на app
```

`app` и `scheduler` используют один пакет и одну БД, но запускаются отдельными процессами. Это исключает дубли планировщика при перезапуске API.

## Поток отправки

1. Кнопка `open_app` открывает Mini App.
2. Frontend передаёт `window.WebApp.initData` в заголовок `X-Init-Data`.
3. Backend проверяет подпись и находит пользователя по MAX ID.
4. Каталоги загружаются поисковыми запросами, а не одним гигантским списком.
5. `POST /api/reports` в одной транзакции сохраняет шапку и строки.
6. Связанное обязательство становится `submitted` или `late`.
7. В той же транзакции создаётся outbox event; worker после commit отправляет краткую карточку в рабочую группу с retry.

## Поток контроля

1. Scheduler создаёт обязательства на дату из активных назначений ответственный–объект.
2. В заданные часы выбирает `pending` и публикует напоминание с ФИО и объектами.
3. Утром закрывает просроченные как `missed` и публикует итог предыдущего дня.
4. `notification_log` с уникальным ключом не допускает повторной отправки.

## Табель

В БД хранятся нормализованные строки. Широкая таблица `показатель × дни` строится запросом при чтении и экспорте. Отдельные дневные колонки в БД запрещены.

Группировка: объект → категория → показатель → единица → день. Суммировать разные единицы нельзя.

## Управление справочниками

Администратор/менеджер редактирует каталоги в Mini App на экране `/admin/catalogs`: табы для объектов, этапов, подрядчиков, единиц, техники, видов и способов работ, связей и назначений. Soft-delete через `active=false`. Bulk-загрузка через Excel (`/api/catalogs/import/*`, `/api/catalogs/export.xlsx`).

## Поиск

Каталоги имеют `code`, `name`, `search_aliases`, `active`, `sort_order`. Поиск выполняется на backend по нормализованной строке; для PostgreSQL используется `pg_trgm`. Frontend запрашивает не более 20–50 результатов с debounce.

## Dev-режим

При `APP_ENV=dev` (а не только `DEBUG=true`) backend добавляет dev-only middleware: все API-запросы без реального `initData` привязываются к placeholder-пользователю `dev-user`. Frontend в production-сборке может использовать `VITE_ALLOW_DEV_AUTH=true`, чтобы отправлять `X-Init-Data: dev` — это нужно только для локального теста в браузере. В production с реальным MAX dev-auth отключён.

## Надёжность

- Все изменения отчёта — одна транзакция.
- Повторный POST защищён `Idempotency-Key`.
- Уникальность отчёта задаётся обязательством `дата + объект + ответственный`.
- В строках отчёта сохраняются snapshot-названия.
- Scheduler/outbox worker используют уникальные keys и PostgreSQL lock.
- В production используется MAX webhook и HTTPS.
- SPA-fallback в FastAPI отдаёт `index.html` для любого пути, кроме `/api/*` и `/assets/*`, чтобы глубокие frontend-маршруты (`/admin/catalogs`) работали после reload.

