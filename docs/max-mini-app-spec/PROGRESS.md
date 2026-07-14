# PROGRESS

Обновлено: 2026-07-14.

## Текущий статус

I18 завершена. Excel экспорт табеля.

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
| I11 | COMPLETED | Техника и перерсонал |
| I12 | COMPLETED | Работы и submit |
| I13 | COMPLETED | MAX REST client, webhook handler, тесты |
| I14 | COMPLETED | Групповой/личный пульт управления |
| I15 | COMPLETED | Карточка после отчёта |
| I16 | COMPLETED | Табель API |
| I17 | COMPLETED | Табель UI |
| I18 | COMPLETED | Excel табеля |
| I19–I22 | WAIT | Выполняются строго по порядку |

## Текущая итерация: I19

Следующий агент делает только I19 из `08_implementation_plan.md`.

## Чек-лист I19

- [ ] Scheduler worker, advisory lock, create obligations.
- [ ] Два вечерних reminder jobs.
- [ ] Показывает только pending; ФИО + объекты.
- [ ] Второй запуск не дублирует.
- [ ] Timezone test.
- [ ] Тесты и lint зелёные.
- [ ] Обновлён `PROGRESS.md` и один коммит.

## HANDOFF NOTES

### 2026-07-14 — I18 завершена

**Агент:** kimi-k2.7-code:cloud  
**Ветка:** docs/max-mini-app-spec  
**Итерация:** I18 — Excel табеля  
**Коммит:** `<TBD>`

**Сделано:**
- Backend:
  - `app/services/timesheet_excel_service.py`: `TimesheetExcelBuilder`.
  - Листы: `Общая сводка`, `Статус отправки`, лист объекта (по коду), `Исходные отчёты`.
  - Заголовки, автоширина колонок, закрепление шапки/первых колонок.
  - Пропущенные дни выделены цветом.
  - Итоговые колонки выделены жирным.
  - Имена листов очищены от запрещённых символов и ограничены 31 символом.
  - `app/api/timesheet.py`: `GET /api/timesheet/{object_id}/export.xlsx` с RBAC.
- Tests:
  - `tests/test_timesheet_excel.py`: workbook структура, листы, данные объекта, отсутствие чужого объекта.

**Проверки:**
- `make test` → 153 passed.
- `make lint` → All checks passed!

**Блокер/риск:**
- Нет.

**Следующий единственный шаг:**
- I19: scheduler reminders.

**Изменённые файлы:**
- `max_daily_report/app/services/timesheet_excel_service.py` (new)
- `max_daily_report/app/api/timesheet.py`
- `max_daily_report/tests/test_timesheet_excel.py` (new)
- `docs/max-mini-app-spec/PROGRESS.md`
