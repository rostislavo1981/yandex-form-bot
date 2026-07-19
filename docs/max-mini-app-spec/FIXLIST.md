# FIXLIST — исправления по код-ревью 2026-07-14

> **ИСТОРИЧЕСКИЙ ДОКУМЕНТ.** Все пункты F1–F7 закрыты.
> Актуальный статус находится в PROGRESS.md (R00–R14 DONE, R15 ручная приёмка).

**СТАТУС: все группы закрыты 2026-07-15.** Коммиты: F1 `d242f4a`, F2 `2e6eab6`, F3 `aa36346`, F4 `a37802c`, F5 `96fee19`, F6 `054169a`; F7-тесты входят в коммиты своих групп. Итог: 112 backend + 10 frontend тестов зелёные, ruff/tsc чистые. Остаточный `[непроверено]` — только wire-формат MAX API (F6.4), закрывается живой сверкой при подключении реального бота.

Источник: полное код-ревью `max_daily_report/` (74 backend + 10 frontend тестов зелёные, ruff чистый — но тесты покрывают только dev-путь; все пункты ниже подтверждены чтением кода).

Правила работы со списком:
- Исправлять **строго по порядку групп** (F1 → F2 → …). Внутри группы можно параллелить.
- Каждый пункт = фикс + **регресс-тест**, доказывающий проблему (сначала красный, потом зелёный).
- После закрытия пункта — отметить `[x]` и добавить hash коммита.
- Не расширять скоуп пункта «полезными улучшениями».

---

## F1. КРИТИЧНО: авторизация (без этого прод нефункционален)

- [x] **F1.1. Общий auth-dependency на все роутеры.**
  Сейчас все защищённые endpoints читают `request.state.user`, который заполняет только dev-middleware при `APP_ENV=dev` (`app/main.py:49-70`). Валидация initData подключена только к `/api/auth/me` (`app/api/auth.py`). Заголовок `X-Init-Data` от фронта (`frontend/src/api/client.ts:32`) везде кроме `/me` игнорируется → в проде всё 401.
  **Сделать:** dependency `require_user` (валидация `X-Init-Data` → User из БД; в dev — fallback), подключить через `dependencies=[...]`/параметры ко всем роутерам: reports, submission, timesheet, catalogs, admin_catalogs, import_export, control_panel. Удалить копипасту `_extract_user` из 4 файлов.

- [x] **F1.2. Закрыть неавторизованные мутирующие endpoints.**
  - `POST /api/catalogs/import/apply` и `/validate` (`app/api/import_export.py`) — сейчас кто угодно перезаписывает справочники. Требовать role admin (manager?) — сверить со спекой.
  - `POST /api/scheduler/*` (`app/api/scheduler.py`) — сейчас внешний POST переводит obligations в missed и шлёт сообщения в группу. Закрыть внутренним shared-secret (`X-Internal-Token` из settings) и/или не проксировать через Caddy.
  - `POST /api/worker/process-outbox` (`app/api/worker.py`) — аналогично.

- [x] **F1.3. `GET /api/reports/{id}` без auth и без проверки прав** (`app/api/reports.py:105`). Добавить auth + ownership: responsible видит только свои.

- [x] **F1.4. Поиск справочников без auth** (`app/api/catalogs.py`). Добавить auth; `search_objects` для роли responsible фильтровать по активным назначениям (спека: «объекты ограничены назначениями»).

## F2. КРИТИЧНО: webhook / бот

- [x] **F2.1. Callback `my_reports` падает на несуществующих полях** (`app/api/webhook.py:116-126`): `DailyReport.user_id`, `r.object_name`, `r.submitted_at` не существуют (реально: `responsible_user_id: int FK`, `object_id`, `created_at`); сравнивается int FK со строковым max_user_id. Переписать через join User по max_user_id и Object по object_id. Добавить тест на callback `my_reports`.

- [x] **F2.2. Telegram-ссылка + утечка токена** (`app/api/webhook.py:105`): `https://t.me/{MAX_BOT_TOKEN.split(':')[0]}?startapp=report` — чужой мессенджер и префикс токена в чате. Заменить на `https://max.ru/<bot_username>?startapp=report`, username хранить в settings (`MAX_BOT_USERNAME`). Тест: в тексте сообщения нет фрагментов токена.

- [x] **F2.3. Мёртвые кнопки.** Бот рассылает `group_status:*`, `timesheet:*`, `timesheet_excel:*`, `retry_report:*` (`app/services/scheduler_service.py:62,151-156`, `app/services/notification_worker.py:88-91`), но webhook обрабатывает только `open_report` и `my_reports`. Реализовать обработчики или убрать кнопки из рассылок. Пульты из SUMMARY §Пульты не реализованы.

## F3. ВЫСОКИЙ: валидация отчёта

- [x] **F3.1. Отчёт «только работы» отклоняется** (`app/schemas/reports.py:56-70`): валидатор `at_least_one_detail` на поле `equipment` срабатывает до парсинга `works`. Перенести проверку в `@model_validator(mode="after")`. Тест: works-only без staff/soil → 201.

- [x] **F3.2. `soil_export_m3=0` считается содержимым** (`app/services/report_service.py:255`): `is not None` → `> 0`. Синхронизировать со схемой.

- [x] **F3.3. Отрицательный персонал принимается** (`app/schemas/reports.py:9-12`): добавить `Field(ge=0)` на itr/internal/external. Тест: `itr=-5` → 422.

- [x] **F3.4. Повторный отчёт за тот же день/объект → 500** (`app/services/report_service.py:281-318`): фильтр `status=="pending"` не находит уже submitted obligation → INSERT нарушает `UNIQUE(report_date, assignment_id)`. Плюс `scalar_one()` (строка 303) кидает NoResultFound. Вернуть явный 409 «отчёт за эту дату уже сдан». Тест: два POST с разными Idempotency-Key → второй 409, не 500.

- [x] **F3.5. Несуществующие id → 500 вместо 422** (`app/services/report_service.py:74-91`): `_get(EquipmentType/Unit/WorkType, ...)` может вернуть None, но результат разыменовывается без проверки. Добавить None-проверки с ReportValidationError (по образцу method).

## F4. ВЫСОКИЙ: табель и обязательства

- [x] **F4.1. Персонал и грунт затираются при двух отчётах в день** (`app/services/timesheet_service.py:61-65`): присваивание вместо накопления. Заменить на `+=` (как у техники/работ). Тест: два отчёта одного дня → персонал суммирован.

- [x] **F4.2. Average считается по дням с данными** (`app/services/timesheet_service.py:166`), спека: «по календарным дням, где ожидался отчёт». Делить на `len(expected_days ∩ период)` (уточнить крайний случай: expected=0).

- [x] **F4.3. Обязательства вне периода назначения** (`app/services/obligation_service.py:35-39`): добавить фильтры `active_from <= date <= active_to`. Тест: assignment истёк вчера → сегодня obligations не создаются.

- [x] **F4.4. Статус `late` никогда не наступает**: `_update_obligation` всегда ставит `submitted` без сравнения с `due_at`; сводка всегда покажет late=0. Ставить `late`, если `now > due_at`. Согласовать с ответом `late` в `POST /api/reports`.

- [x] **F4.5. `due_at` — naive datetime, tz игнорируется** (`app/services/obligation_service.py:16`): 23:59 «UTC» = 02:59 следующего дня по Москве. Использовать `zoneinfo` и tz группы.

## F5. ВЫСОКИЙ: scheduler / надёжность

- [x] **F5.1. Повторный сбой уведомления → crash на UNIQUE** (`app/services/scheduler_service.py:237-254`): `_record_failed` всегда INSERT с тем же `notification_key`. Сделать get-or-create + increment attempts. Тест: два подряд сбоя → attempts=2, без IntegrityError.

- [x] **F5.2. Advisory lock не переживает первый commit** (`app/database.py:13` NullPool + `app/services/scheduler_service.py:175-184`): соединение закрывается на внутреннем commit → лок снимается; release идёт на другом соединении (no-op). Использовать `pg_try_advisory_xact_lock` в одной транзакции либо выделенное соединение на весь job.

- [x] **F5.3. Fire-and-forget задачи могут исчезнуть** (`app/scheduler_runner.py:93-97`): `asyncio.create_task` без хранения ссылки — GC может убить task. Передавать coroutine-функции в APScheduler напрямую (он поддерживает async) или хранить ссылки.

- [x] **F5.4. Карточка отчёта суммирует разные единицы** (`app/services/notification_worker.py:157-162`): `sum(w.quantity ...)` смешивает метры/штуки/рейсы — нарушение правила спеки. Группировать по единице или показывать количество строк.

## F6. СРЕДНИЙ

- [x] **F6.1.** `str(user_info.get("id"))` → `"None"` truthy (`app/api/auth.py:136`). Проверять до str().
- [x] **F6.2.** Двойной URL-decode в валидации initData (`app/api/auth.py:58`): `parse_qsl` уже декодирует, `unquote` поверх исказит значения с `%`. Сверить с официальным вектором валидации MAX и добавить тест с ним (план I09 требовал — теста нет).
- [x] **F6.3.** Подмена ответственного менеджером не реализована (спека UX): в `ReportCreateRequest` нет `responsible_user_id`; `_validate` требует assignment у автора — менеджер без назначения не сдаст отчёт. Добавить опциональное поле + проверку роли.
- [x] **F6.4.** Формат MAX API — гипотезы без пометок: `{"type":"inline_keyboard","inline_keyboard":...}` и `callback_data` (`app/services/max_client.py:38`, `app/api/webhook.py:63`) против `payload.buttons`/`payload` из `05_max_integration.md`; `chatId`/`msgId` camelCase. Свериться с официальной документацией, исправить, пометить остаточные гипотезы `[непроверено]`, добавить контракт-тест на JSON тела.
- [x] **F6.5.** SPA-fallback перехватывает неизвестные `/api/*` → 200 c index.html (`app/main.py:82`). Отдавать 404 для `/api/*`.
- [x] **F6.6.** `Caddyfile` — только `:80`, без HTTPS. Для прода нужен вариант с доменом и авто-TLS (MAX Mini App требует HTTPS).
- [x] **F6.7.** Стиль/мелочи: конструкция из `__import__` (`app/api/reports.py:51-71`) → нормальные импорты; `-> any` builtin вместо `Any` (`app/services/report_service.py:342`); затенение `user` + N+1 в `submission_status` (`app/services/report_service.py:170-193`); `payload_json: Mapped[dict]` при колонке Text; `_pending_obligations(group_id)` игнорирует параметр (`app/services/scheduler_service.py:195-206`); dev-middleware открывает сессию БД на каждый запрос (`app/main.py:55`).

## F7. Тесты (закрывается вместе с пунктами выше)

- [x] Прод-путь auth: запрос с валидным initData без dev-режима → 200; без заголовка → 401.
- [x] Webhook `my_reports`, `retry_report`, `group_status`.
- [x] Works-only отчёт; отрицательный персонал; дубль дня → 409.
- [x] Табель: два отчёта в день; average по expected.
- [x] Obligations: период назначения; late.
- [x] Notification log: повторный сбой.

---

## Порядок работ

| Шаг | Группа | Оценка |
|---|---|---|
| 1 | F1 (auth) | 0.5–1 день |
| 2 | F2 (webhook) | 0.5 дня |
| 3 | F3 (валидация отчёта) | 0.5 дня |
| 4 | F4 (табель/obligations) | 0.5–1 день |
| 5 | F5 (scheduler) | 0.5 дня |
| 6 | F6+F7 (средние + добивка тестов) | 1 день |

Каждый шаг — отдельная ветка `codex/fix-fN-<slug>`, один коммит на пункт или логичную пачку, DoD: `make lint && make test && make frontend-check` зелёные + новые регресс-тесты.
