# 09. Тестирование

## Стек
- `pytest` + `pytest-asyncio` — backend.
- `httpx.AsyncClient` через `ASGITransport` — интеграционные тесты API.
- Отдельная тестовая PostgreSQL БД через docker.

## Уровни

### 1. Unit
- `test_webapp_auth.py`: валидная подпись → dict; неправильный hash → error; auth_date > 24ч → error; пустая строка → error.
- `test_report_service.py`: инварианты (чужой этап, отсутствие подрядчика, пустое содержимое).
- `test_excel_service.py`: сгенерированный файл открывается openpyxl, содержит 3 листа, правильные заголовки.

### 2. Интеграционные (API)
- `test_health.py`: 200 без auth.
- `test_bootstrap.py`: возвращает 8 ключей, справочники не пустые.
- `test_reports_create.py`:
  - happy path own → 201, запись в БД, 3 таблицы.
  - contractor без contractor_id → 400.
  - stage.object_id ≠ report.object_id → 400.
  - все `quantity=0` и нет вывоза → 400.
- `test_reports_list.py`: фильтр по датам, по объекту, `mine=true`.
- `test_summary.py`: агрегаты корректны (сравнить с ручным SQL-подсчётом).
- `test_export_xlsx.py`: скачать файл, распарсить openpyxl, проверить кол-во строк.

### 3. Bot
- `test_max_client.py`: моки httpx, проверка формата запросов к `getUpdates` / `sendMessage`.
- `test_handlers.py`: `/report` вызывает `send_message` с web_app-кнопкой.

### 4. Frontend
В MVP — ручное тестирование по чек-листу (см. ниже). Автотесты (Playwright/vitest) — пост-MVP.

## Чек-лист ручного тестирования (перед мержем в main)

### Сценарий 1: own-объект
- [ ] `/` открывается, справочники подгружены.
- [ ] Дата = сегодня по умолчанию.
- [ ] Выбор объекта БОГ-КЛ-04 → в списке этапов только его этапы.
- [ ] Поле «подрядчик» скрыто.
- [ ] Блок «персонал» виден.
- [ ] Добавляется строка техники, unit подставляется автоматически.
- [ ] Удаление строки работает.
- [ ] Отправка успешна, показан ID.
- [ ] В БД появилась запись + строки.

### Сценарий 2: contractor-объект
- [ ] Выбор РСТИ-БКТП-3 → появилось поле «подрядчик» с дефолтным значением.
- [ ] Блок «персонал» скрыт.
- [ ] Отправка работает.

### Сценарий 3: валидация
- [ ] Отправка без техники/работ/грунта → 400 «Добавьте технику…».
- [ ] quantity = 0 → 400.
- [ ] Пустой ответственный → блокировка кнопки.

### Сценарий 4: сводная
- [ ] `/summary` показывает N карточек.
- [ ] Чипы «7 дней» / «30 дней» меняют выборку.
- [ ] Excel скачивается, содержит данные.

### Сценарий 5: MAX (после Phase 5)
- [ ] `/start` → приветствие с командами.
- [ ] `/report` → кнопка открывает Mini App.
- [ ] Отправка внутри MAX работает.
- [ ] Запрос без initData в prod → 401.

## Как запускать

```
make test              # весь backend
make test-fast         # только unit (без db)
make lint              # ruff
```

`conftest.py` поднимает тестовую БД через event `session`-фикстуру:
```python
@pytest.fixture(scope="session")
def event_loop(): ...

@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()
```

Изолируем тесты откатом транзакции после каждого.

## CI (пост-MVP)

`.github/workflows/ci.yml`:
1. Поднять postgres в service.
2. `pip install -r requirements.txt`.
3. `ruff check .`.
4. `pytest`.

Порог покрытия: 70% на старте, 80% через месяц.
