# PROGRESS

Обновлено: 2026-07-14.

## Текущий статус

I06 завершена. Модели отчётов, обязательств и сервис генерации obligations готовы.

| Итерация | Статус | Результат |
|---|---|---|
| I00 | COMPLETED | Скелет `max_daily_report/`, health, PostgreSQL compose, тест |
| I01 | COMPLETED | База и миграции |
| I02 | COMPLETED | Seed справочников |
| I03 | COMPLETED | Поиск каталогов |
| I04 | COMPLETED | Excel validate |
| I05 | COMPLETED | Excel apply/export |
| I06 | COMPLETED | Модели отчётов и obligations |
| I07–I22 | WAIT | Выполняются строго по порядку |

## Текущая итерация: I07

Следующий агент делает только I07 из `08_implementation_plan.md`.

## Чек-лист I07

- [ ] `POST /api/reports` — сохранение отчёта с idempotency key.
- [ ] Бизнес-инварианты: объект+этап, contractor для contractor-объектов, допустимый способ работы.
- [ ] Транзакция: отчёт + строки + обновление obligation + outbox event.
- [ ] Повтор с тем же key возвращает тот же результат.
- [ ] Чужой этап/объект/способ отвергаются; rollback проверен.
- [ ] Тесты pytest и ruff зелёные.
- [ ] Добавлен handoff и один коммит.

## HANDOFF NOTES

### 2026-07-14 — I06 завершена

**Агент:** kimi-k2.7-code:cloud
**Ветка:** codex/i00-skeleton
**Итерация:** I06 — Модели отчётов и obligations
**Коммит:** `<TBD>`

**Сделано:**
- Добавлены модели в `app/models/reports.py`:
  - `ResponsibleObjectAssignment` — назначение ответственного на объект с schedule_type daily/weekdays.
  - `ReportObligation` — обязательство сдать отчёт на дату со статусами pending|submitted|late|missed|exempt.
  - `DailyReport` — заголовок отчёта с полями персонала, грунта, комментария, idempotency_key.
  - `ReportEquipment` / `ReportWork` — строки техники и работ со snapshot-ами имён и единиц.
  - `NotificationLog` / `OutboxEvent` — операционные таблицы для уведомлений и событий.
- Миграция `b8f81b9a3983_add_reports_obligations_assignments_...` создана Alembic, дополнена `DROP TYPE IF EXISTS ... CASCADE` для enum.
- `ObligationService` в `app/services/obligation_service.py` генерирует obligations по диапазону дат:
  - Учитывает `schedule_type == weekdays` (пропускает субботу/воскресенье).
  - Идемпотентный: повторный запуск не создаёт дубли.
  - Считает `created` и `skipped`.
- Тесты `tests/test_obligations.py` покрывают:
  - 3 объекта × 3 дня → 9 obligations.
  - Weekdays исключает выходные.
  - Повторная генерация не дублирует записи.

**Не сделано:**
- `POST /api/reports`, валидация и транзакция сохранения отчёта (I07).
- Frontend, MAX-интеграция — далее.

**Проверки:**
- `alembic downgrade base && alembic upgrade head` → OK.
- `make test` → 28 passed.
- `make lint` → All checks passed!

**Blocker/риск:**
- Нет.

**Следующий единственный шаг:**
- I07: endpoint POST /api/reports с бизнес-инвариантами и транзакцией.

**Изменённые файлы:**
- `max_daily_report/app/models/reports.py`
- `max_daily_report/app/models/__init__.py`
- `max_daily_report/app/services/obligation_service.py`
- `max_daily_report/app/migrations/versions/b8f81b9a3983_add_reports_obligations_assignments_.py`
- `max_daily_report/tests/test_obligations.py`
- `docs/max-mini-app-spec/PROGRESS.md`
