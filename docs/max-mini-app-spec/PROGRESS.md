# PROGRESS

Обновлено: 2026-07-14.

## Текущий статус

I04 завершена. Excel-шаблон и endpoint validate без изменения БД работают.

| Итерация | Статус | Результат |
|---|---|---|
| I00 | COMPLETED | Скелет `max_daily_report/`, health, PostgreSQL compose, тест |
| I01 | COMPLETED | База и миграции |
| I02 | COMPLETED | Seed справочников |
| I03 | COMPLETED | Поиск каталогов |
| I04 | COMPLETED | Excel validate |
| I05 | NEXT | Excel apply/export |
| I06–I22 | WAIT | Выполняются строго по порядку |

## Текущая итерация: I05

Следующий агент делает только I05 из `08_implementation_plan.md`.

## Чек-лист I05

- [ ] `POST /api/catalogs/import/{import_id}/apply` — транзакционное применение проверенного импорта.
- [ ] `GET /api/catalogs/export.xlsx` — экспорт текущих каталогов.
- [ ] Round-trip export→validate.
- [ ] Ошибка откатывает всё.
- [ ] Отсутствующая строка не деактивируется.
- [ ] `pytest` и `ruff check .` зелёные.
- [ ] Добавлен handoff и один коммит.

## HANDOFF NOTES

### 2026-07-14 — I04 завершена

**Агент:** kimi-k2.7-code:cloud
**Ветка:** codex/i00-skeleton
**Итерация:** I04 — Excel validate
**Коммит:** 450e440

**Сделано:**
- Добавлен `app/services/excel_service.py` с `build_template()` и `CatalogImportValidator`.
- Шаблон содержит листы: Users, Objects, Stages, ObjectStages, Contractors, Units, Equipment, WorkTypes, WorkMethods, WorkTypeMethods, Assignments.
- Endpoint `POST /api/catalogs/import/validate` читает .xlsx, нормализует пробелы и булевы, проверяет обязательные поля, дубли code и enum-значения.
- Возвращает preview `create/update/deactivate` и список ошибок. База не изменяется.
- Добавлен `python-multipart` в зависимости для UploadFile.
- Тесты `tests/test_excel_validate.py` покрывают: valid preview, duplicate code, invalid enum, non-xlsx rejection, template sheets.

**Не сделано:**
- Apply импорта и экспорт каталогов (I05); отчёты, MAX — далее.

**Проверки:**
- `make test` → 153 passed.
- `make lint` → All checks passed!

**Blocker/риск:**
- Нет.

**Следующий единственный шаг:**
- I05: apply импорта одной транзакцией + export каталогов + round-trip test.

**Изменённые файлы:**
- `max_daily_report/pyproject.toml`
- `max_daily_report/app/main.py`
- `max_daily_report/app/api/import_export.py`
- `max_daily_report/app/services/excel_service.py`
- `max_daily_report/tests/test_excel_validate.py`
- `docs/max-mini-app-spec/PROGRESS.md`
