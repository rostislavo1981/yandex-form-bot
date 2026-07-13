# PROGRESS

Обновлено: 2026-07-14.

## Текущий статус

I02 завершена. Seed справочников работает идемпотентно через `python -m app.seed`.

| Итерация | Статус | Результат |
|---|---|---|
| I00 | COMPLETED | Скелет `max_daily_report/`, health, PostgreSQL compose, тест |
| I01 | COMPLETED | База и миграции |
| I02 | COMPLETED | Seed справочников |
| I03 | NEXT | Поиск каталогов |
| I04–I22 | WAIT | Выполняются строго по порядку |

## Текущая итерация: I03

Следующий агент делает только I03 из `08_implementation_plan.md`.

## Чек-лист I03

- [ ] Endpoints objects, stages, equipment, work-types, methods, units.
- [ ] Нормализация входящего query и pagination.
- [ ] Тест поиска по части русского названия, code, alias.
- [ ] inactive не возвращается; этап чужого объекта не возвращается.
- [ ] `pytest` и `ruff check .` зелёные.
- [ ] Добавлен handoff и один коммит.

## HANDOFF NOTES

### 2026-07-14 — I02 завершена

**Агент:** kimi-k2.7-code:cloud
**Ветка:** codex/i00-skeleton
**Итерация:** I02 — Seed справочников
**Коммит:** 44f09b9

**Сделано:**
- Реализован `app/seed.py` с идемпотентными `seed()` (async) и `seed_sync()` (sync для тестов).
- Seed создаёт пользователей, рабочую группу, членство в группе, подрядчиков, единицы измерения, этапы, объекты, связи объект-этап, типы техники, виды работ, способы работ и связи вид-способ.
- Добавлен `CatalogRepo` в `app/repos/catalogs.py` для get_or_create/ensure операций.
- Подключён CLI: `python -m app.seed` и entry point `mdr-seed`.
- Добавлен тест `tests/test_seed.py`: двойной запуск не создаёт дубли; проверяет валидность связей object-stage.

**Не сделано:**
- API endpoints для поиска каталогов (I03); отчёты, Excel, MAX — далее по плану.

**Проверки:**
- `cd max_daily_report && ../.venv/bin/python -m app.seed` → Seed completed successfully (дважды, без дублей).
- `make test` → 153 passed.
- `make lint` → All checks passed!

**Blocker/риск:**
- Нет.

**Следующий единственный шаг:**
- I03: endpoints objects, stages, equipment, work-types, methods, units с поиском и pagination.

**Изменённые файлы:**
- `max_daily_report/pyproject.toml`
- `max_daily_report/app/seed.py`
- `max_daily_report/app/repos/catalogs.py`
- `max_daily_report/app/repos/__init__.py`
- `max_daily_report/tests/test_seed.py`
- `docs/max-mini-app-spec/PROGRESS.md`
