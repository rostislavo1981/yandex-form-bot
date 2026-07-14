# PROGRESS

Обновлено: 2026-07-14.

## Текущий статус

I15 завершена. Карточка после отчёта через outbox worker.

| Итерация | Статус | Результат |
|---|---|---|
| I00 | COMPLETED | Скелет `max_daily_report/`, health, PostgreSQL compose, тест |
| I01 | COMPLETED | База и миграции |
| I02 | COMPLETED | Seed справочников |
| I03 | COMPLETED | Поиск каталогов |
| I04 | COMPLETED | Excel validate |
| I05 | COMPLETED | Excel apply/export |
| I06 | COMPLETED | Модели отчётов и obligations |
| I07 | COMPLETED | POST отчёта |
| I08 | COMPLETED | Чтение и статус отчётов |
| I09 | COMPLETED | Frontend shell, MAX Bridge, initData verify |
| I10 | COMPLETED | SearchSelect и основные поля формы |
| I11 | COMPLETED | Техника и персонал |
| I12 | COMPLETED | Работы и submit |
| I13 | COMPLETED | MAX REST client, webhook handler, тесты |
| I14 | COMPLETED | Групповой/личный пульт управления |
| I15 | COMPLETED | Карточка после отчёта |
| I16–I22 | WAIT | Выполняются строго по порядку |

## Текущая итерация: I16

Следующий агент делает только I16 из `08_implementation_plan.md`.

## Чек-лист I16

- [ ] Timesheet service/API отдельно по объекту.
- [ ] Два объекта не смешиваются.
- [ ] Разные units не складываются.
- [ ] personnel total/avg/max корректны.
- [ ] missing отличается от zero.
- [ ] Тесты и lint зелёные.
- [ ] Обновлён `PROGRESS.md` и один коммит.

## HANDOFF NOTES

### 2026-07-14 — I15 завершена

**Агент:** kimi-k2.7-code:cloud  
**Ветка:** docs/max-mini-app-spec  
**Итерация:** I15 — Карточка после отчёта  
**Коммит:** `<TBD>`

**Сделано:**
- Backend:
  - `app/services/notification_worker.py`: `NotificationWorker` читает pending outbox events, публикует карточку отчёта в активную группу.
  - Eager loading `works` + `equipment` через `selectinload` для async-сессии.
  - Idempotency: notification key `report:{report_id}:{group_id}` + проверка `status == sent`.
  - Retry: временные ошибки увеличивают `attempts`, оставляют `pending` до 5 попыток.
  - Карточка содержит дату, объект, ФИО, работы, технику, грунт, персонал.
  - Кнопки: "Повторить" и "Статус".
  - `app/api/worker.py`: `POST /api/worker/process-outbox` для ручного/scheduler запуска.
  - `app/main.py`: подключён `worker.router`.
- Tests:
  - `tests/test_notification_worker.py`: успешная публикация, idempotency, retry после ошибки.
  - Добавлен `async_session` fixture в `tests/conftest.py` с `NullPool`.

**Проверки:**
- `make test` → 54 passed.
- `make lint` → All checks passed!

**Блокер/риск:**
- Нет.

**Следующий единственный шаг:**
- I16: табель API.

**Изменённые файлы:**
- `max_daily_report/app/services/notification_worker.py` (new)
- `max_daily_report/app/api/worker.py` (new)
- `max_daily_report/app/main.py`
- `max_daily_report/tests/conftest.py`
- `max_daily_report/tests/test_notification_worker.py` (new)
- `docs/max-mini-app-spec/PROGRESS.md`
