# PROGRESS

Обновлено: 2026-07-14.

## Текущий статус

I01 завершена. Схема users/groups/catalogs создана через Alembic, test DB fixture работает на реальном PostgreSQL.

| Итерация | Статус | Результат |
|---|---|---|
| I00 | COMPLETED | Скелет `max_daily_report/`, health, PostgreSQL compose, тест |
| I01 | COMPLETED | База и миграции |
| I02 | NEXT | Seed справочников |
| I03–I22 | WAIT | Выполняются строго по порядку |

## Текущая итерация: I02

Следующий агент делает только I02 из `08_implementation_plan.md`.

## Чек-лист I02

- [ ] Минимальный seed users/objects/stages/units/equipment/work types.
- [ ] Идемпотентная команда `python -m app.seed`.
- [ ] Два запуска не создают дубли.
- [ ] Связи object-stage валидны.
- [ ] `pytest` и `ruff check .` зелёные.
- [ ] Добавлен handoff и один коммит.

## HANDOFF NOTES

### 2026-07-14 — I01 завершена

**Агент:** kimi-k2.7-code:cloud
**Ветка:** codex/i00-skeleton
**Итерация:** I01 — База и миграции
**Коммит:** 64f60e1

**Сделано:**
- Настроена async SQLAlchemy: `app/database.py`, `app/models/base.py`.
- Инициализирован Alembic: `alembic.ini`, `app/migrations/env.py` с async-движком.
- Созданы модели users (`users`, `max_groups`, `group_members`) и catalogs (`contractors`, `objects`, `stages`, `object_stages`, `units`, `equipment_types`, `work_types`, `work_methods`, `work_type_methods`).
- Первая миграция `1a2e795e0f06` создаёт все таблицы и extension `pg_trgm`.
- Добавлен test DB fixture в `tests/conftest.py` (sync psycopg2 для стабильности) с truncate всех таблиц перед каждым тестом.
- Тест `tests/test_database.py` вставляет строки во все таблицы и проверяет чтение.

**Не сделано:**
- Отчёты, Excel, MAX integration — вне scope I01.

**Проверки:**
- `../.venv/bin/alembic upgrade head` → OK.
- `../.venv/bin/alembic downgrade base && ../.venv/bin/alembic upgrade head` → OK.
- `make test` → 2 passed.
- `make lint` → All checks passed!

**Blocker/риск:**
- pytest-asyncio 0.23+ конфликтовал с asyncpg по event loop. Решено использованием sync psycopg2-binary только в тестах.

**Следующий единственный шаг:**
- I02: seed справочников (users/objects/stages/units/equipment/work types) + идемпотентная команда `python -m app.seed`.

**Изменённые файлы:**
- `max_daily_report/pyproject.toml`
- `max_daily_report/alembic.ini`
- `max_daily_report/app/migrations/env.py`
- `max_daily_report/app/migrations/versions/1a2e795e0f06_initial_schema_users_groups_catalogs.py`
- `max_daily_report/app/models/__init__.py`
- `max_daily_report/app/models/base.py`
- `max_daily_report/app/models/catalogs.py`
- `max_daily_report/app/models/users.py`
- `max_daily_report/tests/conftest.py`
- `max_daily_report/tests/test_database.py`
- `docs/max-mini-app-spec/PROGRESS.md`
