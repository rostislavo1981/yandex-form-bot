# 08. План коротких итераций

## Правила для агента

1. Выполняй только одну итерацию за сессию, если пользователь не попросил больше.
2. Перед кодом прочитай только указанные для итерации документы.
3. Не делай TODO следующей итерации.
4. Добавь тест, запусти команды DoD, обнови `PROGRESS.md`, сделай один коммит.
5. Если DoD красный — не переходи дальше и не маскируй ошибку.
6. Не меняй контракт без записи в `DECISIONS.md`.

Каждая итерация рассчитана примерно на 2–4 часа и должна оставлять запускаемое состояние.

## I00 — Скелет

Читать: `SUMMARY.md`, `07_project_structure.md`.

Сделать: создать `max_daily_report/`, Python package, FastAPI `/api/health`, Settings, Dockerfile, compose с PostgreSQL, Makefile, один smoke test.

DoD: `docker compose up -d db`; `pytest`; `ruff check .`; health test 200.

Не делать: модели предметной области, frontend, MAX.

## I01 — База и миграции

Читать: `03_data_model.md`.

Сделать: async SQLAlchemy, Alembic с первой миграцией для users/groups/catalogs и extension `pg_trgm`; test DB fixture.

DoD: upgrade с пустой БД; downgrade/upgrade; тест видит таблицы.

Не делать: отчёты и Excel.

## I02 — Seed справочников

Сделать: минимальный seed users/objects/stages/units/equipment/work types и идемпотентную команду `python -m app.seed`.

DoD: два запуска не создают дубли; связи object-stage валидны.

## I03 — Поиск каталогов

Читать: `04_api_contract.md`, `13_catalogs_excel.md`.

Сделать: endpoints objects, stages, equipment, work-types, methods, units; нормализация и pagination.

DoD: тест поиска по части русского названия, code, alias; inactive не возвращается; этап чужого объекта не возвращается.

## I04 — Excel validate

Сделать: шаблон книги и endpoint validate без записи в каталоги.

DoD: valid preview показывает create/update; duplicate code и битая ссылка возвращают понятные ошибки; БД не изменилась.

## I05 — Excel apply/export

Сделать: apply только validated import одной транзакцией; export текущих каталогов.

DoD: round-trip export→validate; ошибка откатывает всё; отсутствующая строка не деактивируется.

*Примечание: в I22 добавлена упрощённая web-админка `/admin/catalogs` для CRUD и Excel import/export; bulk-шаблоны остаются прежними.*

## I06 — Модель отчётов и obligations

Читать: `03_data_model.md` разделы назначений и отчётов.

Сделать: миграция assignments, obligations, reports, equipment/works, notification log, outbox events; сервис генерации obligations.

DoD: assignment на 3 объекта создаёт 3 obligations; повторный запуск без дублей; weekdays исключает выходной.

## I07 — POST отчёта

Сделать: `POST /api/reports`, бизнес-инварианты, транзакция, idempotency, обновление obligation.

DoD: happy path; повтор с тем же key возвращает тот же результат; чужой этап и недопустимый объект отвергаются; rollback проверен.

## I08 — Чтение и статус

Сделать: list/detail reports и submission-status.

DoD: expected/submitted/pending/late корректны на fixture с двумя людьми и тремя объектами; права responsible/manager проверены.

## I09 — Frontend shell и auth

Читать: `05_max_integration.md`, `06_frontend_spec.md`.

Сделать: Vite React TS, routes, API client, MAX Bridge, backend verify initData, dev-only auth.

DoD: TS build; unit tests официального validation vector; production без initData → 401; dev fallback не работает в prod.

## I10 — SearchSelect и основные поля

Сделать: объект, этап, дата, ответственный, contractor; SearchSelect states.

DoD: поиск работает; смена объекта очищает этап; responsible видит только назначения; mobile smoke.

## I11 — Техника и персонал

Сделать: EquipmentRows, ownership отдельно, default unit, quantity; персонал.

DoD: добавить/удалить две строки; единица подставляется; отрицательное и пустое не отправляется.

## I12 — Работы и submit

Сделать: WorkRows, допустимые способы, грунт, комментарий, submit с UUID key, success.

DoD: полный сценарий UI→API→DB; двойной клик не создаёт дубль; понятны ошибки API.

## I13 — MAX client и webhook

Читать: `05_max_integration.md`, официальную MAX docs на дату реализации.

Сделать: REST client `/messages`, `/subscriptions`, edit, pin; webhook с secret; handlers `bot_started`, callback/message buttons.

DoD: mock HTTP проверяет URL/header/body; webhook reject bad secret; raw payload не содержит секретов в логах.

## I14 — Видимые пульты

Читать: `15_group_bot.md`.

Сделать: клавиатуры, `ensure_group_control_panel`, `ensure_private_control_panel`, хранение message IDs, role-based actions.

DoD: групповой пульт создаётся, обновляется и закрепляется; личный восстанавливается `/start` и `/menu`; повтор не плодит сообщения без причины.

## I15 — Карточка после отчёта

Сделать: создавать outbox event в транзакции отчёта; worker публикует краткую карточку и кнопки с retry и notification key.

DoD: DB failure не создаёт публикацию; временная ошибка MAX оставляет retry; повтор не дублирует; карточка содержит объект, ФИО и итоги.

## I16 — Табель API

Читать: `14_timesheet.md`.

Сделать: timesheet service/API отдельно по объекту.

DoD: два объекта не смешиваются; разные units не складываются; personnel total/avg/max корректны; missing отличается от zero.

## I17 — Табель UI

Сделать: выбор объекта/периода, mobile table, sticky columns, категории и итоги.

DoD: 31-дневный период читаем на мобильной ширине; loading/empty/error; responsible не открывает чужой объект.

## I18 — Excel табеля

Сделать: листы summary/status/object/raw, форматирование и download endpoint.

DoD: workbook открывается openpyxl; каждый объект на своём листе; контрольные суммы равны API; имена листов безопасны.

## I19 — Scheduler reminders

Читать: `15_group_bot.md`.

Сделать: worker, advisory lock, create obligations, два вечерних reminder jobs.

DoD: показывает только pending; ФИО + объекты; второй запуск не дублирует; timezone test.

## I20 — Утренняя сводка

Сделать: pending прошлого дня → missed; expected/submitted/late/missed; кнопки status/timesheet/Excel.

DoD: fixture 12/9/1/3 отображается правильно; список missing содержит ФИО и объекты; повтор безопасен.

## I21 — Production deploy

Сделать: Caddy HTTPS, compose app/scheduler/db/caddy, migrations at deploy, healthchecks, backup command, webhook registration runbook.

DoD: чистый VPS поднимается по README; реальные group/private buttons; реальный submit; уведомление; scheduler dry-run; backup создаётся.

## I22 — Приёмка MVP

Пройти полный чек-лист `09_testing_plan.md`, исправить только blockers, обновить документацию и tag release candidate.

DoD: все automated tests, lint, TS build, real MAX smoke, Excel reconciliation, user acceptance на одном ответственном и двух объектах.

*Примечание: в рамках финальной приёмки добавлена упрощённая админ-страница `/admin/catalogs` (CRUD + Excel import/export) для менеджеров/админов.*
