# REMEDIATION PLAN — исправления после ревью 2026-07-15

## Цель

Довести `max_daily_report/` до проверяемого MVP: динамическая форма, отдельный
табель каждого объекта, краткие отчёты и напоминания в общей группе MAX,
рабочие видимые кнопки, Excel и безопасный production-запуск.

**Release candidate: BLOCKED.** Тег RC запрещён до закрытия R15.

## Правила работы для агента

1. За один заход выполнять только одну итерацию.
2. Перед началом прочитать `AGENT_START_HERE.md`, верх `PROGRESS.md` и нужный
   раздел этого файла; проверить `git status`.
3. Сначала добавить тест, воспроизводящий дефект, затем исправить код.
4. Не использовать реальные токены, initData и персональные данные в fixtures.
5. Не запускать backend-тесты до закрытия R00.
6. Не расширять scope соседними улучшениями.
7. Итерация = тесты + код + HANDOFF в `PROGRESS.md` + один коммит.
8. Если нужны домен, токен, реальная группа, восстановление/очистка не-test БД
   или бизнес-решение — остановиться и запросить пользователя.

## Общий Definition of Done

- дефект закрыт регресс-тестом;
- целевые тесты и lint/build зелёные;
- `git diff --check` чистый;
- в diff нет secrets, дампов и PII;
- документация не объявляет непроверенную функцию готовой;
- в `PROGRESS.md` записан один следующий шаг.

## Порядок итераций

| ID | Статус | P | Зависит от | Результат |
|---|---|---:|---|---|
| R00 | ✅ DONE | P0 | — | Отдельная test DB; `mdr_db` защищена |
| R01 | ✅ DONE | P0 | R00 | Официальный MAX REST client |
| R02 | ✅ DONE | P0 | R01 | Официальный webhook/Update |
| R03 | ✅ DONE | P0 | R01–R02 | Публичный HTTPS/443 и subscription |
| R04 | ✅ DONE | P0 | R00–R01 | Постоянный outbox worker и retry |
| R05 | ✅ DONE | P0 | R02–R04 | Все пульты и кнопки работают |
| R06 | ✅ DONE | P1 | R00 | Динамические единицы без подмены |
| R07 | ✅ DONE | P1 | R06 | Подрядные объекты заполняются |
| R08 | ✅ DONE | P1 | R00 | Один отчёт на obligation, нет race |
| R09 | ✅ DONE | P1 | R00 | Реальные страницы отчётов и статуса |
| R10 | ✅ DONE | P1 | R08–R09 | Корректный накопительный табель |
| R11 | ✅ DONE | P1 | R00 | Полный Excel round-trip каталогов |
| R12 | ✅ DONE | P1 | R10 | Полный Excel-табель и download UI |
| R13 | ✅ DONE | P1 | R00–R12 | CI проверяет весь продукт |
| R14 | ✅ DONE | P2 | R00 | Auth/input hardening и legacy cleanup |
| R15 | 🚫 BLOCKED | P0 | R01–R14 | Реальная MAX production acceptance |
| R16 | ✅ DONE | P1 | R15 | Документация обновлена |

R00–R05 выполнены строго последовательно. R06–R14 выполнены после R05.

---

## R00. Изолировать тестовую БД

**Цель:** тесты физически не могут выполнить `TRUNCATE` в `mdr_db`.

**Файлы:** `max_daily_report/tests/conftest.py`, `Makefile`, compose, README.

**Сделать:**

- создать отдельную `mdr_test` и повторяемую команду её подготовки;
- `make test` передаёт `TEST_DATABASE_URL`, не `DATABASE_URL`;
- fixture до очистки проверяет `current_database()` и разрешает только имя,
  заканчивающееся на `_test`;
- guard срабатывает до первого `TRUNCATE`;
- описать: текущая локальная `mdr_db` была очищена во время ревью;
  восстановление выполняется только по отдельному подтверждению пользователя.

**Тесты:** guard отклоняет `mdr_db`, принимает `mdr_test`; полный backend suite
проходит; контрольная строка в `mdr_db` после suite не меняется.

**Не делать:** не восстанавливать backup и не очищать рабочую БД.

**Коммит:** `test(R00): isolate PostgreSQL test database`

## R01. Исправить MAX REST client

**Цель:** outbound запросы совпадают с актуальным официальным API.

**Файлы:** `app/services/max_client.py`, contract fixtures/tests.

**Сделать:**

- `POST /messages`: `chat_id`/`user_id` в query, в body только NewMessageBody;
- `PUT /messages`: `message_id` в query;
- нормализованно извлекать официальный message id из ответа;
- реализовать `answer_callback` через `POST /answers`;
- оставить подтверждённый `attachments[].payload.buttons`;
- использовать `settings.max_api_base_url`, единый async client и безопасные
  ошибки без token/request body;
- fixtures брать из официальной схемы или обезличенного реального ответа.

**Тесты:** `MockTransport` проверяет method/path/query/headers/JSON/response для
send, edit, pin, callback answer и subscribe; `chatId`/`msgId` в body запрещены.

**DoD:** остальные сервисы получают нормализованный `message_id` и не знают
wire-формат. Коммит: `fix(R01): align MAX REST client with official API`.

## R02. Исправить webhook и официальный Update

**Цель:** реальные `bot_started` и `message_callback` проходят endpoint.

**Файлы:** `app/api/webhook.py`, webhook tests и fixtures.

**Сделать:**

- сравнивать `X-Max-Bot-Api-Secret` с configured secret; убрать HMAC тела;
- читать `update_type`, `chat_id`, `user.user_id` и официальный `callback`;
- ответить на callback методом из R01;
- group actions принимать только из configured active group;
- personal actions ограничивать нажавшим пользователем;
- `bot_started` не выдаёт повышенную роль;
- unknown update → 200/ignored, wrong secret → 401;
- не логировать raw payload, phone, initData или secret.

**Тесты:** официальные JSON fixtures; right/wrong/missing secret; старый
camelCase fixture больше не считается эталоном.

**DoD:** в handler отсутствуют `type == callback`, `chatId`, `userId` и
`x-signature`. Коммит: `fix(R02): parse official MAX updates`.

## R03. Production HTTPS/443 и регистрация webhook

**Цель:** standalone production compose доступен MAX на публичном 443.

**Файлы:** prod compose, Caddyfile, `register_webhook.sh`, `.env.example`, README.

**Сделать:**

- production ports `80:80` и `443:443`; 8080/8443 только local override;
- preflight отклоняет пустые token/secret/internal token, localhost,
  `DOMAIN=:80` и не-HTTPS production URL;
- subscription содержит явные `update_types`, включая `bot_started` и
  `message_callback`;
- добавить read-only просмотр subscriptions и health smoke;
- сверить актуальные TLS/CA требования и `platform-api2.max.ru`;
- дополнительно закрыть scheduler/worker paths в Caddy, сохранив internal token.

**Тесты:** `docker compose config`, shell lint, негативные preflight tests,
локальный smoke. Реальную subscription в автоматическом тесте не создавать.

**DoD:** runbook содержит один однозначный публичный URL без номера порта.
Коммит: `fix(R03): expose production webhook on HTTPS 443`.

## R04. Запустить надёжный outbox worker

**Цель:** после commit приходит ровно одна карточка; временная ошибка повторяется.

**Файлы:** notification worker, новый runner, compose, при необходимости
миграция lease metadata.

**Сделать:**

- отдельный постоянно работающий worker service;
- claim через транзакцию и `FOR UPDATE SKIP LOCKED`;
- использовать `processing`, lease/stale recovery, ограниченный batch;
- exponential backoff в `available_at`, лимит попыток, last_error;
- отсутствие active group не помечает событие `done`;
- notification key предотвращает повторную карточку после restart;
- healthcheck и корректный SIGTERM;
- карточка: дата, объект, этап, ФИО, персонал и суммы по совместимым units.

**Тесты:** success, 429/500, backoff, final failure, stale processing, no group,
два worker и restart после отправки.

**DoD:** compose restart не теряет и не дублирует событие.
Коммит: `fix(R04): run reliable outbox worker`.

## R05. Сделать все кнопки видимыми и рабочими

**Цель:** пользователь не обязан знать slash-команды.

**Файлы:** control panel service, webhook, keyboard builder, deep links, tests.

**Сделать:**

- единые callback-константы для builder/parser;
- групповой пульт: Заполнить, Статус, Табель, Excel, Кто не сдал, Помощь;
- личный: Заполнить, Мои отчёты, Мой табель, Мои объекты, Excel, Группа;
- Mini App открывать подтверждённой `open_app`/link-кнопкой, не callback с
  последующей текстовой ссылкой;
- реализовать status/timesheet/excel/refresh/help handlers;
- ensure group panel при старте и утром, private panel при bot_started/menu и
  после завершённых действий;
- пересоздавать и закреплять удалённый group panel.

**Тесты:** таблица «каждая видимая кнопка → payload → handler → эффект»; ни одного
payload без handler; кнопка заполнения есть в обоих пультах.

**Коммит:** `fix(R05): make all MAX control buttons actionable`

## R06. Динамические единицы техники и работ

**Цель:** машино-часы, рейсы, метры, штуки и м³ не смешиваются.

**Сделать:**

- catalog DTO техники/работ возвращает `default_unit_id` и unit label;
- UI подставляет default, но позволяет выбрать другую active unit;
- удалить поиск `кубометр`/`м³` из `EquipmentRows` и `WorkRows`;
- SearchSelect показывает реальный выбранный code/name;
- при смене типа сбрасывать несовместимую unit;
- backend проверяет существование/active unit.

**Тесты:** минимум машино-час, рейс, метр, шт, м³; payload и табель сохраняют
их раздельно. Коммит: `fix(R06): use dynamic units and defaults`.

## R07. Подрядные объекты

**Цель:** contractor object можно отправить из Mini App.

**Сделать:**

- object DTO: `execution_method`, `default_contractor_id`;
- защищённый поиск active contractors;
- условное поле подрядчика и подстановка default;
- backend требует существующего active contractor;
- правило contractor для own object закрепить в DECISIONS;
- смена объекта очищает stage/contractor.

**Тесты:** own success; contractor default/manual success; missing, inactive и
unknown contractor → 422. Коммит: `fix(R07): support contractor reports`.

## R08. Инварианты и конкурентная отправка

**Цель:** на obligation максимум один итоговый отчёт.

**Сделать:**

- DB unique `(report_date, responsible_user_id, object_id)` или эквивалент через
  obligation — выбрать один источник истины;
- `SELECT FOR UPDATE` obligation;
- одинаковый idempotency key возвращает исходный result, разные ключи одного
  obligation → 409, без 500;
- active validation stage/equipment/unit/work type/method/contractor;
- snapshot только после полной валидации;
- IntegrityError → rollback + доменная ошибка;
- migration останавливается с понятным blocker при существующих дублях.

**Тесты:** конкурентный `asyncio.gather` с одинаковыми/разными keys; ровно один
report/outbox; inactive refs → 422.

**Коммит:** `fix(R08): enforce one report per obligation`

## R09. Реальные страницы «Отчёты» и «Статус»

**Цель:** удалить placeholder из основной навигации.

**Сделать:**

- Reports: pagination, date/object/user filters, detail, late и краткие суммы;
- responsible видит свои, manager/admin — все разрешённые;
- Status: expected, submitted (включая late как заполненные), late отдельно,
  pending/missed, ФИО и объект;
- единое определение counters для UI/API/morning summary;
- один auth provider вместо повторных `/me` на Layout и страницах;
- role guards, loading/error/retry/empty states.

**Тесты:** роли, filters, pagination, late, missing FIO, frontend components;
в страницах нет `I13`/`I20` placeholder.

**Коммит:** `feat(R09): implement reports and status pages`

## R10. Корректный накопительный табель

**Цель:** отдельный табель объекта различает пропуск, partial, ноль и выходной.

**Сделать:**

- по дню вернуть expected/submitted/late/missing counts и status
  `not_expected|submitted|partial|missed`;
- один из трёх reports не закрывает весь день;
- день без obligation не считать «сданным»;
- sums разделять по item + ownership/method + unit;
- personnel считать как человеко-дни, average — по документированным expected
  calendar days;
- доступ responsible ограничить периодом assignment;
- валидировать from/to и ограничить максимальный период;
- сохранить строгий фильтр object_id.

**Тесты:** два объекта, две units, три responsible в день, partial, weekend,
late, assignment range и все итоги.

**Коммит:** `fix(R10): represent per-obligation timesheet status`

## R11. Полный Excel import/export справочников

**Цель:** ни один из 11 листов шаблона не игнорируется.

**Сделать:**

- import/export Users и Assignments;
- WorkTypeMethods использует словари work types/methods, не objects;
- `active=0` работает для ObjectStages и WorkTypeMethods;
- validate headers, references, enums, dates/ranges, unknown default unit;
- честный create/update/deactivate preview;
- atomic apply и rollback;
- лимит upload и защита от чрезмерного XLSX/ZIP;
- определить round-trip правило active/inactive строк;
- записывать безопасное filename и результат в catalog_imports.

**Тесты:** полный export→edit→validate→apply→export всех листов; relations,
deactivate, bad ref, duplicate, oversized и rollback.

**Коммит:** `fix(R11): complete catalog Excel round trip`

## R12. Полный Excel-табель и скачивание

**Цель:** Excel выбранного объекта равен данным Timesheet API.

**Сделать:**

- листы: сводка, статус, объект, реальные исходные отчёты;
- autofilter/freeze/widths/safe sheet name;
- ноль пустой; missing/partial/not_expected различаются стилем;
- total/average/max брать из API результата;
- raw rows: report/date/user/stage и факты для аудита;
- API client скачивает blob с `X-Init-Data`;
- видимая Excel-кнопка на TimesheetPage;
- group Excel открывает авторизованный выбор object/period, если отправка файла
  через MAX не входит в MVP.

**Тесты:** openpyxl проверяет values/filter/freeze/styles/raw; frontend проверяет
authenticated download. Коммит: `feat(R12): finish timesheet Excel export`.

## R13. CI для всего продукта

**Цель:** зелёный PR проверяет legacy и MVP.

**Сделать:**

- jobs: legacy Python; MVP backend + PostgreSQL; frontend Node 20; Docker build;
- MVP использует только `mdr_test`, применяет migrations, lint/tests;
- frontend: `npm ci`, build, tests;
- `alembic check` после migrations;
- Docker image health smoke без secrets;
- branch protection требует MVP jobs.

**Проверка:** контролируемая временная ошибка MVP обязана сделать CI красным;
ошибку удалить до коммита. Коммит: `ci(R13): validate complete MVP`.

## R14. Auth/input hardening и legacy cleanup

**Сделать:**

- malformed/missing `auth_date` → 401, не 500;
- разрешённый возраст `-clock_skew..TTL`, параметры в settings;
- max lengths для comments, idempotency key и search;
- upload limit до полного чтения в память;
- production preflight требует internal token;
- исправить/удалить отсутствующий `backend.cli.build_summary` entry point;
- README ясно отделяет архивный V1 от MVP.

**Тесты:** malformed/future/expired initData, oversized inputs/files, console
entry point import smoke. Коммит: `fix(R14): harden auth and packaging`.

## R15. Реальная production-приёмка MAX

**Предусловия от пользователя:** staging/production domain, token, webhook secret,
тестовая группа и разрешение регистрировать subscription/писать сообщения.
Без этого записать blocker и остановиться.

**Перед началом:** подтверждённый backup, clean git, R00–R14 зелёные, bot имеет
write/pin, secrets только в `.env`.

**Сценарий:**

1. HTTPS/443, certificate chain, health.
2. Зарегистрировать и прочитать subscription.
3. Реальные bot_started и message_callback; сверить sanitized fixtures.
4. Закрепить group panel и пройти каждую group/private кнопку.
5. Проверить реальный `window.WebApp.initData`.
6. Отправить own и contractor reports с разными units.
7. После каждого получить ровно одну карточку.
8. Проверить retry на временной ошибке без дубля.
9. Запустить reminders на явную test date, сверить ФИО/объекты.
10. Запустить morning summary, сверить counters с obligations.
11. Открыть табели объектов и скачать Excel.
12. Restart API/worker/scheduler — сообщений повторно нет.
13. В логах нет token, secret, initData, phone.

**Артефакт:** обезличенный acceptance report с PASS/FAIL и временем. Любой FAIL
возвращает работу в соответствующую итерацию; tag запрещён.

## R16. Документация и решение о RC

**Сделать:**

- синхронизировать SUMMARY, API/MAX/frontend specs, testing plan и README;
- записать подтверждённый MAX contract и версию fixtures;
- quick start, migrate, worker, backup/restore/rollback runbooks;
- убрать ложные completed и `[непроверено]` либо оставить явный blocker;
- полный прогон из clean checkout;
- только после PASS попросить пользователя подтвердить создание RC tag.

**Финальные команды:**

```bash
make lint && make test
cd max_daily_report
make lint && make test && make frontend-check
env DATABASE_URL=postgresql+asyncpg://.../mdr_test ../.venv/bin/alembic check
docker compose -f docker-compose.prod.yml config
docker compose -f docker-compose.prod.yml build
```

**Коммит:** `docs(R16): finalize release readiness`

---

## Финальная матрица

| Область | Обязательная проверка |
|---|---|
| Данные | Tests работают только с `mdr_test`; backup/restore проверен |
| MAX inbound | Реальные bot_started/message_callback проходят |
| MAX outbound | send/edit/pin/answer подтверждены реальным API |
| Кнопки | Все group/private кнопки видимы и имеют эффект |
| Отчёт | Own + contractor, разные units, duplicate/race защищены |
| Группа | После submit ровно одна краткая карточка |
| Напоминания | Только pending, корректные ФИО/объекты |
| Утро | expected/submitted/late/missed равны obligations |
| Табель | Отдельно по объектам, дни, partial, суммы/average/max |
| Excel | Catalog round-trip; timesheet XLSX равен API |
| Restart | Worker/scheduler не теряют и не дублируют события |
| CI | Legacy + backend + frontend + migrations + image зелёные |
| Docs | Нет ложного RC и неподтверждённого контракта |

## Условия немедленной остановки

- R00 не закрыта, но требуется backend test suite;
- требуется восстановить/очистить не-test БД;
- официальный MAX payload расходится с fixtures;
- нужен реальный token/domain/group без явного разрешения;
- migration обнаружила существующие дубли reports;
- требуется новое бизнес-правило;
- в целевых файлах есть пересекающиеся чужие изменения.
