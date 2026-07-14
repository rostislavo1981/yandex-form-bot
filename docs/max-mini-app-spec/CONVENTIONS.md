# CONVENTIONS

## Работа

- Одна ветка/коммит на итерацию: `codex/iXX-short-name` и `feat: IXX краткий результат`.
- Перед изменением прочитать iteration и DoD.
- Не трогать V1 `backend/`; новый код только в `max_daily_report/`.
- Не начинать следующую итерацию автоматически.
- `PROGRESS.md` обновляется в каждом завершённом/заблокированном шаге.

## Python

- Python 3.12+, полные type hints, `from __future__ import annotations`.
- Ruff, line length 100, double quotes.
- FastAPI/SQLAlchemy async; `asyncpg`; никаких `time.sleep`.
- HTTP в `app/api`/`app/max`, бизнес-правила в `services`, SQL в `repos`.
- Прикладные ошибки переводятся в русский `{"detail":"..."}`.
- Никаких `except Exception: pass` и raw secrets/PII в логах.

## TypeScript

- Strict, функциональные компоненты, hooks, без `any`.
- `PascalCase.tsx` для компонентов, `useCamelCase.ts` для hooks.
- API типы централизованы в `frontend/src/api/` и `frontend/src/types/`.
- Обязательны loading/empty/error/success состояния.

## БД

- Изменение схемы только Alembic migration.
- FK/UNIQUE/CHECK там, где правило возможно выразить в БД.
- Catalog delete запрещён: `active=false`.
- Money/quantity через Decimal/NUMERIC, не float в бизнес-расчётах.
- Любой retry-sensitive side effect имеет idempotency key.

## Тесты

- Feature → минимум один test; bugfix → regression test.
- PostgreSQL logic тестируется на реальной test DB, не mock ORM.
- Mock допустим для MAX HTTP и времени scheduler.
- Перед handoff: `make lint`, `make test`, `make frontend-check` для итераций после появления frontend.

## Секреты

Только `.env`; `.env.example` содержит пустые значения. Запрещено коммитить bot token, webhook secret, initData, телефоны, дампы и логи.

## Definition of Done

- Реализован только scope итерации.
- Автотест демонстрирует результат.
- Все команды DoD зелёные.
- Документирован любой изменённый контракт.
- `PROGRESS.md` содержит точный handoff.
- Один осмысленный коммит.
