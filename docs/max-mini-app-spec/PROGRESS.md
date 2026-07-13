# 📊 PROGRESS — журнал прогресса

**Это живой файл. Каждая сессия его обновляет.**

Правила:
- Работающий агент помечает свою фазу 🚧 и обновляет чек-лист.
- В конце сессии — обязательно заполняется `HANDOFF NOTE` (шаблон см. в [`HANDOFF_TEMPLATE.md`](./HANDOFF_TEMPLATE.md)).
- Не удалять историю — только добавлять новые записи вниз.

---

## Общий статус

| Phase | Название | Статус | Ветка | PR |
|---|---|---|---|---|
| 0 | Bootstrap | ⬜ Не начата | — | — |
| 1 | Модель данных и БД | ⬜ Не начата | — | — |
| 2 | Создание и чтение отчётов | ⬜ Не начата | — | — |
| 3 | Frontend MVP | ⬜ Не начата | — | — |
| 4 | Сводная и Excel | ⬜ Не начата | — | — |
| 5 | Bot MAX + HMAC | ⬜ Не начата | — | — |
| 6 | Прод-деплой | ⬜ Не начата | — | — |

Легенда: ⬜ не начата · 🚧 в работе · ✅ завершена · ⛔ заблокирована

---

## 🚧 Текущая фаза

**Ни одна фаза не начата.** Следующий шаг: **Phase 0 — Bootstrap**.

Первому агенту, приступающему к работе:
1. Прочитать `AGENT_START_HERE.md`.
2. Создать ветку `phase-0-bootstrap`.
3. Идти по чек-листу Phase 0 в [`08_implementation_plan.md`](./08_implementation_plan.md).
4. По завершении — обновить эту таблицу и добавить HANDOFF NOTE ниже.

---

## Чек-лист Phase 0 (Bootstrap)

Скопируй пункты из [`08_implementation_plan.md`](./08_implementation_plan.md) §Phase 0 и отмечай:

- [ ] git init, README, .gitignore, .dockerignore, LICENSE
- [ ] Дерево папок из `07_project_structure.md`
- [ ] docker-compose.yml (db + backend)
- [ ] backend/requirements.txt
- [ ] backend/Dockerfile
- [ ] backend/app/main.py с /api/health
- [ ] backend/app/config.py (Settings)
- [ ] .env.example
- [ ] Makefile
- [ ] **DoD:** `curl localhost:8000/api/health` → `{"status":"ok"}`

---

## Чек-лист Phase 1 (Модель данных)

*(разворачивается, когда Phase 0 закрыта)*

---

## Чек-лист Phase 2 (Отчёты)

*(разворачивается позже)*

---

## Чек-лист Phase 3 (Frontend)

*(разворачивается позже)*

---

## Чек-лист Phase 4 (Сводная и Excel)

*(разворачивается позже)*

---

## Чек-лист Phase 5 (Bot MAX + HMAC)

*(разворачивается позже)*

---

## Чек-лист Phase 6 (Прод-деплой)

*(разворачивается позже)*

---

## 📌 HANDOFF NOTES

Здесь каждая сессия оставляет запись **по шаблону из [`HANDOFF_TEMPLATE.md`](./HANDOFF_TEMPLATE.md)**. Свежие — сверху.

---

### [2026-07-13] — Сверка с реальной документацией MAX Bot API

**Агент:** Claude Opus 4.7
**Фаза:** пре-Phase 0 (только документация)
**Что сделал:**
- Сверил `05_max_integration.md` с [dev.max.ru/docs](https://dev.max.ru/docs) и [dev.max.ru/docs-api](https://dev.max.ru/docs-api).
- Полностью переписал `05_max_integration.md` под реальный API: base URL `platform-api2.max.ru`, авторизация header'ом, REST-стиль endpoints (`POST /messages`, `GET /updates`, `POST /subscriptions`, `POST /answers`, `POST /uploads`).
- Добавил 7 типов кнопок MAX (`callback`, `link`, `open_app`, `message`, `request_contact`, `request_geo_location`, `clipboard`) с примерами. Ключевое — `message` для пульта в группе.
- Скорректировал формулу HMAC verify_init_data: `HMAC_SHA256(auth_date + phone + user_id, bot_token)` — отличается от Telegram.
- Задокументировал deep-link `https://max.ru/<bot>?startapp=<payload>` для запуска отчёта из группы.
- **DECISIONS.md:** ADR-003 помечен «отменено ADR-008»; ADR-005 «уточнено ADR-009»; добавлены ADR-008 (API MAX ≠ Telegram) и ADR-009 (webhook сразу после деплоя).
- **12_track_A_bot_first.md:** Phase A3 переписана под реальные endpoints MAX, добавлен раздел webhook. Phase A5 переписана: HTTPS всё же нужен (для `/webhook/max`).
- **08_implementation_plan.md:** Phase 5 обновлена — HMAC-формула и REST-методы MAX.
- **10_glossary.md:** добавлены startapp, attachments, message_callback, POST /answers, Пульт, Deep-link.

**Что НЕ сделал:**
- Файлы `13_bot_conversation.md`, `14_group_notifications.md`, `15_group_controls.md` пока не созданы — их писать в момент реализации Phase A3/A4.5, чтобы не расходились с реальностью.
- В `05_max_integration.md` §5.17 остались 8 `[непроверено]` пунктов — их надо закрыть логированием реальных updates от тестового бота.

**Следующий шаг:**
Первый агент-разработчик начинает **Phase A0 / Phase 0 — Bootstrap** по трекам A или B (см. `11_two_tracks.md`). Рекомендация — Track A.

---

### [YYYY-MM-DD HH:MM] — Инициализация пакета спецификаций

**Агент:** Claude Opus 4.7
**Фаза:** пре-Phase 0 (только документация)
**Что сделал:**
- Создал 11 файлов спецификаций (`00`…`10`).
- Добавил инфраструктуру для передачи контекста между сессиями:
  `AGENT_START_HERE.md`, `PROGRESS.md`, `CONVENTIONS.md`, `DECISIONS.md`, `HANDOFF_TEMPLATE.md`.

**Что НЕ сделал:**
- Ни одна строка кода не написана.
- Репозиторий проекта `max_daily_report/` ещё не создан.

**Следующий шаг:**
Первый агент-разработчик начинает **Phase 0 — Bootstrap** по [`08_implementation_plan.md`](./08_implementation_plan.md).

**Что важно знать:**
- Пакет лежит в `docs/max-mini-app-spec/` внутри существующего репозитория `yandex-form-bot`.
- Сам проект `max_daily_report` **отдельный** — его нужно создать (в этом же репо в подпапке, или в новом — уточнить у пользователя перед началом).
- Все `[непроверено]` в `05_max_integration.md` требуют сверки с актуальной документацией MAX перед Phase 5.

**Открытые вопросы к пользователю:**
1. Куда создавать проект: подпапка `max_daily_report/` в текущем репо, или новый репозиторий?
2. Есть ли уже токен от BotFather MAX или его получит следующий агент?
3. Есть ли VPS с доменом для Phase 6, или деплой откладываем?
