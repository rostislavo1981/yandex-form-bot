# PROGRESS

Обновлено: 2026-07-14.

## Текущий статус

I05 завершена. Импорт каталогов транзакционно применяется, экспорт каталогов доступен.

| Итерация | Статус | Результат |
|---|---|---|
| I00 | COMPLETED | Скелет `max_daily_report/`, health, PostgreSQL compose, тест |
| I01 | COMPLETED | База и миграции |
| I02 | COMPLETED | Seed справочников |
| I03 | COMPLETED | Поиск каталогов |
| I04 | COMPLETED | Excel validate |
| I05 | COMPLETED | Excel apply/export |
| I06–I22 | WAIT | Выполняются строго по порядку |

## Текущая итерация: I06

Следующий агент делает только I06 из `08_implementation_plan.md`.

## Чек-лист I06

- [ ] Модели отчётов: `Report`, `ReportSection`, `ReportValue`.
- [ ] API сохранения черновика: `POST /api/reports/draft`.
- [ ] Валидация обязательных полей по типу формы.
- [ ] Тесты pytest зелёные.
- [ ] Добавлен handoff и один коммит.

## HANDOFF NOTES

### 2026-07-14 — I05 завершена

**Агент:** kimi-k2.7-code:cloud
**Ветка:** codex/i00-skeleton
**Итерация:** I05 — Excel apply/export
**Коммит:** `<TBD>`

**Сделано:**
- Добавлен `CatalogImportApplier` в `app/services/excel_service.py`:
  - Транзакционное применение валидированного workbook.
  - Порядок загрузки: Contractors → Units → Stages → Objects → ObjectStages → Equipment → WorkTypes → WorkMethods → WorkTypeMethods.
  - При ошибке ссылки (отсутствующий подрядчик/этап/вид работы/способ) выбрасывается ValueError → откат транзакции.
  - Нет автоматической деактивации отсутствующих строк.
- `CatalogImport` получил свойства `summary`/`errors`, обёртывающие JSONB-поля.
- Endpoint `POST /api/catalogs/import/apply` валидирует и применяет файл в одной транзакции.
- Endpoint `GET /api/catalogs/export.xlsx` экспортирует активные каталоги.
- `GET /api/catalogs/template.xlsx` теперь возвращает настоящий файл (ранее был 501).
- `app/database.py` переведён на `async_sessionmaker` + `NullPool` для стабильности тестов с `TestClient`.
- Исправлен баг в `app/services/catalog_service.py`: поиск по коду возвращал лишние записи из-за `and` вместо `&`.
- Тесты `tests/test_excel_apply.py` покрывают:
  - Успешное создание каталогов через apply.
  - Проверку строк в БД после apply.
  - Откат транзакции при некорректной ссылке.
  - Отклонение файла с ошибками валидации.
  - Round-trip validate пустого шаблона.
  - Endpoint export.xlsx.

**Не сделано:**
- Staged apply по `import_id` (заглушка 501 оставлена для будущего).
- Отчёты, MAX-интеграция — далее.

**Проверки:**
- `make test` → 25 passed.
- `make lint` → All checks passed!

**Blocker/риск:**
- Нет.

**Следующий единственный шаг:**
- I06: модели отчётов + сохранение черновика.

**Изменённые файлы:**
- `max_daily_report/app/database.py`
- `max_daily_report/app/models/operations.py`
- `max_daily_report/app/services/catalog_service.py`
- `max_daily_report/app/services/excel_service.py`
- `max_daily_report/app/api/import_export.py`
- `max_daily_report/tests/conftest.py`
- `max_daily_report/tests/test_catalogs.py`
- `max_daily_report/tests/test_excel_apply.py`
- `docs/max-mini-app-spec/PROGRESS.md`
