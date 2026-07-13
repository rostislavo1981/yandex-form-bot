# 📋 SUMMARY — что построено, что решено, что делать дальше

Один документ, дающий полную картину без чтения всех остальных. Если у агента есть только 3 минуты — читать этот файл.

Актуальность: после сверки с [dev.max.ru/docs](https://dev.max.ru/docs) и коммита cc240ee.

---

## 1. Что за продукт

**MAX Mini App «Ежедневный отчёт по объекту»** — сервис, куда прораб сдаёт ежедневный отчёт по строительному объекту прямо из мессенджера MAX. Данные лежат в PostgreSQL, руководитель качает Excel.

**Заменяет** ручное заполнение Яндекс.Формы (V1 в этом же репо — `backend/`). Новый сервис — с нормализованной схемой БД и без LLM.

**Основная сущность** — объект (строительная площадка) с уникальным титулом и способом выполнения (`own` / `contractor`).

---

## 2. Два трека развития (выбирается пользователем)

### Трек A — Bot-first (рекомендуется)
Сначала бот-опросник с inline-кнопками. Прораб отвечает клавишами в чате. Mini App — как второй этап, если понадобится.

- **Готовый MVP** за ~7 дней.
- Плюс Mini App позже — ещё ~7 дней.

### Трек B — MiniApp-first
Сначала React-форма в webview. Быстрее ввод, но дольше первый релиз.

- **Готовый MVP** за ~12 дней.

Оба трека имеют **общее ядро** — PostgreSQL + FastAPI + REST-API отчётов. Ветвление начинается после Phase 2.

Подробнее — [`11_two_tracks.md`](./11_two_tracks.md).

---

## 3. Архитектура (обе версии)

```
       ┌──────────────────┐
       │  Прораб в MAX    │  Android/iOS клиент
       └────────┬─────────┘
                │
   ┌────────────┼─────────────┐
   │            │             │
   ▼            ▼             ▼
Bot API    Mini App        (Личка бота)
long       webview
polling    HTTPS
(dev)      HMAC initData
или
webhook
(prod)
   │            │
   ▼            ▼
┌──────────────────────────────────────┐
│  Bot process        FastAPI          │
│  (Python async)     backend :8000    │
│  - MaxClient        - /api/reports   │
│  - state machine    - /api/summary   │
│  - poller/webhook   - /api/export.xlsx│
└──────────┬───────────────────┬───────┘
           │                   │
           │       SQLAlchemy 2.0 async
           ▼                   ▼
       ┌──────────────────────────┐
       │    PostgreSQL 16         │
       │  objects/stages/         │
       │  daily_reports/          │
       │  report_equipment/       │
       │  report_works/ ...       │
       └──────────────────────────┘

Frontend (только в Track B / Phase A6):
React + Vite + TypeScript, статика,
раздаётся через Caddy на том же :443
```

**Компоненты — процессы docker-compose:**
- `db` — PostgreSQL 16
- `backend` — FastAPI (uvicorn), REST-API + webhook endpoint
- `bot` — Python-процесс, MaxClient + state machine + poller
- `frontend` — только в Track B (React статика через Caddy)
- `caddy` — HTTPS + маршрутизация (нужен даже в Track A ради `/webhook/max`)

---

## 4. Модель данных (PostgreSQL, нормализованная)

10 таблиц:

- **`users`** (id, max_user_id UNIQUE, full_name, role, active)
- **`contractors`** (id, name UNIQUE, active)
- **`objects`** (id, title_code UNIQUE, name, execution_method `own|contractor`, default_contractor_id, active) — **центральная сущность**
- **`stages`** (id, object_id FK, name, active) — этапы, зависят от объекта
- **`units`** (id, name, code) — единицы измерения
- **`equipment`** (id, category, name UNIQUE, default_unit_id, active)
- **`work_types`** (id, category, name UNIQUE, default_unit_id, active)
- **`daily_reports`** — шапка отчёта (дата, ответственный, объект, этап, подрядчик, персонал ИТР/штат/внешт, вывоз грунта, статус)
- **`report_equipment`** — строки техники в отчёте (с snapshot-именем)
- **`report_works`** — строки работ (с snapshot-именем)

Ключевые инварианты (проверяются в API):
1. `stage.object_id == report.object_id`
2. `object.execution_method='contractor' ⇒ report.contractor_id != NULL`
3. Хотя бы одно из: техника, работа, `soil_export_m3 > 0`
4. Все `quantity > 0`, все `staff_* >= 0`

**Snapshot-имена** в строках отчёта позволяют переименовывать справочники без потери исторических данных.

Полностью — [`03_data_model.md`](./03_data_model.md).

---

## 5. REST API (7 эндпоинтов)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/api/health` | Liveness |
| GET | `/api/bootstrap` | Все справочники одним запросом |
| POST | `/api/reports` | Создать отчёт |
| GET | `/api/reports` | Список с фильтрами |
| GET | `/api/reports/{id}` | Полный отчёт со строками |
| GET | `/api/summary` | Агрегаты за период |
| GET | `/api/export.xlsx` | Excel-выгрузка (3 листа: Реестр / Техника / Работы) |

Плюс `/webhook/max` для приёма updates от MAX (prod).

Все запросы к защищённым эндпоинтам обязаны содержать `X-Auth-InitData` (Mini App) или вызываются изнутри compose-сети (bot).

Полные примеры req/resp — [`04_api_contract.md`](./04_api_contract.md).

---

## 6. Интеграция с MAX (проверено по dev.max.ru/docs)

**Base URL:** `https://platform-api2.max.ru`
**Авторизация:** заголовок `Authorization: <MAX_BOT_TOKEN>`

**Ключевые endpoints:**
- `POST /messages` — отправить сообщение (с attachments для кнопок)
- `GET /updates` — long polling (dev)
- `POST /subscriptions` — регистрация webhook (prod)
- `POST /answers` — ответ на callback-кнопку
- `POST /uploads` — загрузка файла, возвращает token для attachment
- `GET/PATCH /chats/{id}` — работа с чатом

**7 типов кнопок:** `callback`, `link`, `open_app`, `message`, `request_contact`, `request_geo_location`, `clipboard`.
Ключевое: `message` — жмёшь, отправляется заготовленный текст (идеально для пульта в группе); `open_app` — открытие mini app; `link` с deep-link — прыжок из группы в личку.

**Deep-link:** `https://max.ru/<bot>?startapp=<payload>` → в webview попадает как `WebApp.initDataUnsafe.start_param`.

**HMAC initData (отличается от Telegram):**
```
hash = HMAC_SHA256(auth_date + phone + user_id, bot_token)
```
Ключ HMAC — сам `bot_token` (без SHA256-обёртки); data-check — конкатенация только 3 полей.

**Update types:** минимум `message_created` и `message_callback`.

Полностью — [`05_max_integration.md`](./05_max_integration.md). Список того, что ещё требует уточнения (8 пунктов) — §5.17.

---

## 7. UX — как это выглядит для прораба

### Track A (бот-опросник)
Прораб пишет `/report` в личке или жмёт `[📝 Сдать отчёт]` в закреплённом пульте группы.
Бот в личке ведёт диалог: дата → объект → этап → техника → персонал → работы → грунт → подтверждение → сохранение.
После сохранения — карточка отчёта уходит в группу для всех.

### Track B (Mini App)
Прораб жмёт кнопку `[📝 Отчёт]` → webview открывает React-форму с dropdown'ами и динамическими строками.
Одна страница, всё видно, отправка одним нажатием.

Обе версии могут работать одновременно поверх общего backend'а.

### В группе (обе версии)
Закреплённое ботом сообщение — «пульт»:
```
[📝 Сдать отчёт]  [📊 Сегодня]  [7 дней]  [30 дней]  [📥 Excel]
```
- «Сдать отчёт» — deep-link в личку с ботом
- «Сводная», «Excel» — кнопки типа `message`, отправляют команду в чат

После каждого отчёта бот шлёт в группу карточку-уведомление (compact/full настраивается через `chat_settings`).

---

## 8. План разработки

### Общее ядро (обязательно, обе версии) — ~4 дня

| Phase | Что | Дней |
|---|---|---|
| 0 | Bootstrap: docker-compose, FastAPI health, конфиг | 1 |
| 1 | Модель данных: 10 таблиц + seed + `/api/bootstrap` | 1 |
| 2 | API отчётов: POST/GET/{id} с инвариантами + тесты | 2 |

**DoD ядра:** через curl можно создать отчёт, он появляется в PostgreSQL с корректными строками.

### Далее — по выбранному треку

**Track A (Bot-first, +3 дня → 7 всего):**
| A3 | MaxClient + state machine диалога | 2 |
| A4 | `/summary`, `/export` в чате | 1 |
| A5 | Прод-деплой + webhook | 1 |
| A4.5 (опц.) | Уведомления и пульт в группе | 2 |
| A6 (опц.) | Mini App поверх готового | 7-8 |

**Track B (MiniApp-first, +8 дней → 12 всего):**
| B1 | Frontend React + Vite + форма | 3 |
| B2 | Сводная + Excel в UI | 1 |
| B3 | Bot + HMAC initData | 3 |
| B4 | Прод-деплой + HTTPS | 1 |

Каждая фаза заканчивается **Definition of Done** — конкретной проверяемой командой (см. [`08_implementation_plan.md`](./08_implementation_plan.md) для B и [`12_track_A_bot_first.md`](./12_track_A_bot_first.md) для A).

---

## 9. Принятые архитектурные решения (ADR)

| # | Решение | Статус |
|---|---|---|
| 001 | PostgreSQL, не SQLite | принято |
| 002 | Bot и Backend — разные процессы | принято |
| 003 | HMAC-схема Telegram-стиля | **отменено ADR-008** |
| 004 | Frontend без UI-либ | принято |
| 005 | Long polling для dev | принято, уточнено ADR-009 |
| 006 | Без Alembic в MVP | принято |
| 007 | Русские тексты в API-ошибках | принято |
| 008 | MAX API — REST-стиль, свой HMAC | принято |
| 009 | Webhook сразу после прод-деплоя | принято |

Полностью — [`DECISIONS.md`](./DECISIONS.md).

---

## 10. Что запрещено

- ❌ Не менять файлы `01`…`10` без явной просьбы пользователя.
- ❌ Не добавлять LLM (YandexGPT, OpenAI), Playwright, Яндекс.Диск, Яндекс.Формы — это другой проект.
- ❌ Не заменять PostgreSQL на SQLite.
- ❌ Не хранить секреты в git.
- ❌ Не выдумывать параметры MAX API — сверять с dev.max.ru/docs; спорное помечать `[непроверено]`.
- ❌ Не переходить к следующей фазе, пока DoD текущей не выполнен.

---

## 11. Файлы в пакете

**Стабильные (ТЗ):**
- [`AGENT_START_HERE.md`](./AGENT_START_HERE.md) — точка входа для агента
- `00_README.md` — оглавление
- `01_overview.md` — что делаем и зачем
- `02_architecture.md` — компоненты и потоки
- `03_data_model.md` — схема БД
- `04_api_contract.md` — REST-контракт
- `05_max_integration.md` — MAX Bot API + Mini App (сверено с docs)
- `06_frontend_spec.md` — React-экраны
- `07_project_structure.md` — дерево файлов проекта
- `08_implementation_plan.md` — план (Track B)
- `09_testing_plan.md` — тесты
- `10_glossary.md` — термины
- `11_two_tracks.md` — сравнение треков A и B
- `12_track_A_bot_first.md` — план Track A

**Живые (обновляются каждой сессией):**
- `SUMMARY.md` — этот файл (обновлять при существенных изменениях архитектуры)
- `PROGRESS.md` — журнал прогресса + HANDOFF NOTES
- `DECISIONS.md` — ADR-журнал
- `CONVENTIONS.md` — стиль кода, коммитов
- `HANDOFF_TEMPLATE.md` — шаблон записи прогресса

---

## 12. Открытые вопросы к пользователю

1. **Куда создавать код проекта:** подпапка `max_daily_report/` в текущем репо или новый репозиторий?
2. **Какой трек выбираем — A или B?** (рекомендация: A)
3. **Есть ли токен от `@MasterBot` MAX?**
4. **Есть ли VPS с доменом для HTTPS?** (нужен и в Track A ради webhook)

---

## 13. Что делать прямо сейчас, если ты новый агент

1. Прочитать этот файл (сделано).
2. Открыть [`AGENT_START_HERE.md`](./AGENT_START_HERE.md) — там пошаговая инструкция как читать остальное.
3. Посмотреть [`PROGRESS.md`](./PROGRESS.md) — там свежая HANDOFF NOTE от предыдущего агента.
4. Спросить пользователя ответы на вопросы из §12 (если не заданы).
5. Начать Phase 0 (общее ядро) — или продолжить с того шага, что записан в PROGRESS.
