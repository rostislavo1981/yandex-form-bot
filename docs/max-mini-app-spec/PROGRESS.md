# PROGRESS

Обновлено: 2026-07-14.

## Текущий статус

I07 завершена. Endpoint `POST /api/reports` сохраняет отчёты с инвариантами, idempotency и транзакцией.

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
| I08–I22 | WAIT | Выполняются строго по порядку |

## Текущая итерация: I08

Следующий агент делает только I08 из `08_implementation_plan.md`.

## Чек-лист I08

- [ ] `GET /api/reports` — список отчётов с фильтрами.
- [ ] `GET /api/reports/{id}` — полный отчёт (уже есть заглушка, нужно довести).
- [ ] `GET /api/submission-status?date=` — статус сдачи по группе.
- [ ] Права responsible/manager/admin.
- [ ] Тесты pytest и ruff зелёные.
- [ ] Добавлен handoff и один коммит.

## HANDOFF NOTES

### 2026-07-14 — I07 завершена

**Агент:** kimi-k2.7-code:cloud
**Ветка:** codex/i00-skeleton
**Итерация:** I07 — POST отчёта
**Коммит:** `<TBD>`

**Сделано:**
- Добавлен `app/schemas/reports.py`:
  - `ReportCreateRequest`, `EquipmentInput`, `WorkInput`, `StaffInput`.
  - Валидация ownership, положительных quantity, обязательности хотя бы одного блока.
- Добавлен `app/services/report_service.py`:
  - Транзакционное создание отчёта, строк техники/работ, обновление obligation, outbox event.
  - Idempotency по `idempotency_key`.
  - Бизнес-инварианты:
    - объект/этап существуют и активны;
    - этап связан с объектом;
    - contractor-объект требует `contractor_id`;
    - пользователь имеет активное назначение на объект на дату отчёта;
    - способ работы допустим для вида работы;
    - отчёт содержит хотя бы одно из: техника, работы, грунт, персонал.
  - Обработка idempotent повторов без дублирования outbox-событий.
- Добавлен `app/api/reports.py`:
  - `POST /api/reports` с обязательным `Idempotency-Key`.
  - `GET /api/reports/{id}` с полным отчётом.
  - Dev-only middleware создаёт/использует реального `dev-user` в БД.
- `app/main.py` подключает `reports.router` и dev-auth middleware.
- Тесты `tests/test_reports.py` покрывают:
  - Happy path с техникой, работами, грунтом, персоналом.
  - Требование contractor для contractor-объекта.
  - Отклонение чужого этапа.
  - Idempotency (повторный запрос возвращает тот же id).
  - Откат при недопустимом/несуществующем способе работы.
  - Получение деталей отчёта.

**Не сделано:**
- Список отчётов, submission-status, права по ролям (I08).
- Frontend, MAX-интеграция — далее.

**Проверки:**
- `make test` → 34 passed.
- `make lint` → All checks passed!
- `alembic upgrade head` → OK.

**Blocker/риск:**
- Нет.

**Следующий единственный шаг:**
- I08: список отчётов, submission-status, права.

**Изменённые файлы:**
- `max_daily_report/app/main.py`
- `max_daily_report/app/api/reports.py`
- `max_daily_report/app/schemas/reports.py`
- `max_daily_report/app/services/report_service.py`
- `max_daily_report/tests/test_reports.py`
- `docs/max-mini-app-spec/PROGRESS.md`
