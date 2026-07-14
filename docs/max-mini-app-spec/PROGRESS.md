# PROGRESS

Обновлено: 2026-07-14.

## Текущий статус

I16 завершена. Табель API по объекту.

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
| I17–I22 | WAIT | Выполняются строго по порядку |

## Текущая итерация: I17

Следующий агент делает только I17 из `08_implementation_plan.md`.

## Чек-лист I17

- [ ] UI выбора объекта/периода для табеля.
- [ ] Mobile table, sticky columns, категории и итоги.
- [ ] 31-дневный период читаем на мобильной ширине.
- [ ] loading/empty/error.
- [ ] responsible не открывает чужой объект.
- [ ] Тесты и lint зелёные.
- [ ] Обновлён `PROGRESS.md` и один коммит.

## HANDOFF NOTES

### 2026-07-14 — I16 завершена

**Агент:** kimi-k2.7-code:cloud  
**Ветка:** docs/max-mini-app-spec  
**Итерация:** I16 — Табель API  
**Коммит:** `<TBD>`

**Сделано:**
- Backend:
  - `app/services/timesheet_service.py`: агрегация отчётов по дням для объекта.
  - Раздельные строки: personnel, soil, equipment (ownership + unit), work (method + unit).
  - Суммы, среднее, максимум по календарным дням периода.
  - `missing_days` = expected obligations без submitted report.
  - Разные единицы не смешиваются (ключ включает unit).
  - Eager loading works/equipment через `selectinload`.
  - `app/api/timesheet.py`: `GET /api/timesheet/{object_id}` с RBAC (responsible только назначенные объекты).
  - `app/main.py`: подключён `timesheet.router`.
- Tests:
  - `tests/test_timesheet.py`: manager видит объект, responsible только назначенные, данные объектов не смешиваются, personnel total/avg/max, missing days.

**Проверки:**
- `make test` → 57 passed.
- `make lint` → All checks passed!

**Блокер/риск:**
- Нет.

**Следующий единственный шаг:**
- I17: табель UI.

**Изменённые файлы:**
- `max_daily_report/app/services/timesheet_service.py` (new)
- `max_daily_report/app/api/timesheet.py` (new)
- `max_daily_report/app/main.py`
- `max_daily_report/tests/test_timesheet.py` (new)
- `docs/max-mini-app-spec/PROGRESS.md`
