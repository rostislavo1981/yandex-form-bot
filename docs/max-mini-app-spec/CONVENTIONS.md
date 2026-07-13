# 📐 CONVENTIONS — правила кода и работы

## Язык интерфейса и документации

- **Русский:** пользовательские тексты (кнопки, сообщения бота, лейблы формы, тексты ошибок для клиента).
- **Английский:** имена переменных, функций, классов, файлов; технические комментарии в коде.
- **Русский:** документация в `docs/` (потому что заказчик и пользователи русскоязычные).

## Python

### Стиль
- Python **3.12+**.
- Форматтер и линтер: `ruff` (одновременно). Конфиг в `pyproject.toml`.
- Строки: двойные кавычки.
- Импорты: сгруппированы (stdlib / third-party / local), сортировка через ruff.
- Максимальная длина строки: 100.

### Типизация
- Полные аннотации типов везде (включая `-> None`).
- `from __future__ import annotations` в модулях с forward-references.
- `Optional[X]` → `X | None` (Python 3.10+).

### Асинхронность
- Весь backend — async (FastAPI + SQLAlchemy 2.0 async).
- `asyncpg` как драйвер PostgreSQL.
- Никаких `time.sleep` — только `await asyncio.sleep`.

### Комментарии и docstring
- Docstring — у публичных функций и классов, кратко.
- Никаких многострочных «эссе». WHY, а не WHAT.
- `TODO(username): <текст>` — если оставляешь незакрытое.
- `# [непроверено]` — если гипотеза по MAX API.

### Обработка ошибок
- Прикладные исключения в `backend/app/errors.py`.
- FastAPI ловит их через `exception_handler` и возвращает `{"detail": "<по-русски>"}`.
- Никаких `except Exception: pass`.

### Структура эндпоинта
```python
@router.post("/reports", response_model=CreateReportResponse, status_code=201)
async def create_report(
    payload: DailyReportIn,
    user: User = Depends(require_max_user),
    db: AsyncSession = Depends(get_db),
) -> CreateReportResponse:
    """Создать ежедневный отчёт."""
    report = await report_service.create_report(db, payload, user)
    return CreateReportResponse(id=report.id, status=report.status)
```

Логика — в `services/`, доступ к БД — в `repos/`, HTTP — в `api/`. Не смешивать.

## TypeScript / React

- **Strict mode** в `tsconfig.json`.
- Функциональные компоненты + хуки. Никаких классов.
- Никаких `any`. Если нужно — `unknown` + typeguard.
- Пропсы описываются интерфейсом рядом с компонентом.
- CSS — обычный, файлы рядом с компонентом или в `src/styles/`.
- Именование:
  - Компоненты: `PascalCase.tsx`.
  - Хуки: `useCamelCase.ts`.
  - Утилиты: `camelCase.ts`.

## Именование файлов и папок

- **snake_case** для Python (`report_service.py`).
- **kebab-case** для CSS/HTML артефактов, если нужно.
- **PascalCase.tsx** для React-компонентов.
- Тесты: `test_<модуль>.py` в `backend/tests/`.

## Git

### Ветки
- `main` — только зелёные состояния.
- Рабочие ветки: `phase-<N>-<slug>`, напр. `phase-2-reports-api`.
- Хотфиксы: `fix-<slug>`.

### Коммиты (Conventional Commits)
Формат: `<type>: <кратко на русском>`.

Типы:
- `feat` — новая функциональность
- `fix` — багфикс
- `docs` — только документация
- `refactor` — без изменения поведения
- `test` — только тесты
- `chore` — инфраструктура, конфиги
- `style` — форматирование

Примеры:
```
feat: /api/reports POST + валидация инвариантов
fix: этап должен принадлежать объекту
docs: обновил PROGRESS после Phase 2
test: добавил кейсы contractor без подрядчика
```

Один коммит — одно осмысленное изменение. Не мешать в один коммит рефакторинг и фичу.

### Pull Request
- Заголовок: `Phase N: <название фазы>`.
- В описании — ссылки на пункты плана и DoD.
- Перед мержем — `make lint && make test` зелёные, PROGRESS обновлён.

### Что запрещено в коммитах
- `.env` с реальными значениями.
- Бинарники > 1 MB.
- Логи, дампы БД.
- Автогенерированные `node_modules/`, `__pycache__/`, `.venv/`.

## Секреты

- Только в `.env` (в `.gitignore`).
- В `.env.example` — пустые/заглушечные значения с комментариями.
- В коде читаются через `Settings` (pydantic-settings). Никаких `os.getenv` вразнобой.

## Логирование

- Стандартный `logging`, конфиг в `main.py`.
- Формат: `%(asctime)s %(levelname)s %(name)s %(message)s`.
- Уровень:
  - `INFO` — старт/остановка сервисов, обработка апдейта, создание отчёта.
  - `WARNING` — 4xx ошибки.
  - `ERROR` — 5xx, исключения.
- Никаких `print()` в проде (кроме `bot.py` при явном dev-режиме).

## Тесты

- Каждая новая функциональность → минимум один тест.
- Каждый bugfix → регрессионный тест, доказывающий фикс.
- Никаких моков SQLAlchemy — используем реальную тестовую БД (см. `09_testing_plan.md`).
- Моки только для внешних HTTP-вызовов (MAX API).

## Definition of Done (для любой задачи)

- [ ] Код написан по конвенциям.
- [ ] Тесты добавлены и зелёные.
- [ ] `ruff check .` без ошибок.
- [ ] Ручной smoke на localhost прошёл.
- [ ] Обновлён `PROGRESS.md`.
- [ ] Если поменяли контракт — обновлён соответствующий файл `04_*.md` или `03_*.md`.
- [ ] Коммит по конвенции.
