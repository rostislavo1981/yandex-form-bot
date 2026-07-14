# PROGRESS

Обновлено: 2026-07-14.

## Текущий статус

I17 завершена. Табель UI.

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
| I11 | COMPLETED | Техника и персонал |
| I12 | COMPLETED | Работы и submit |
| I13 | COMPLETED | MAX REST client, webhook handler, тесты |
| I14 | COMPLETED | Групповой/личный пульт управления |
| I15 | COMPLETED | Карточка после отчёта |
| I16 | COMPLETED | Табель API |
| I17 | COMPLETED | Табель UI |
| I18–I22 | WAIT | Выполняются строго по порядку |

## Текущая итерация: I18

Следующий агент делает только I18 из `08_implementation_plan.md`.

## Чек-лист I18

- [ ] Excel export табеля: листы summary/status/object/raw.
- [ ] Форматирование и download endpoint.
- [ ] Workbook открывается openpyxl.
- [ ] Каждый объект на своём листе.
- [ ] Контрольные суммы равны API.
- [ ] Имена листов безопасны.
- [ ] Тесты и lint зелёные.
- [ ] Обновлён `PROGRESS.md` и один коммит.

## HANDOFF NOTES

### 2026-07-14 — I17 завершена

**Агент:** kimi-k2.7-code:cloud  
**Ветка:** docs/max-mini-app-spec  
**Итерация:** I17 — Табель UI  
**Коммит:** `<TBD>`

**Сделано:**
- Frontend:
  - `frontend/src/api/timesheet.ts`: типы и `fetchTimesheet`.
  - `frontend/src/pages/TimesheetPage.tsx`: выбор объекта (SearchSelect), выбор периода, загрузка табеля, группировка по категориям, sticky колонки, итог/средн/макс, missing days.
  - `frontend/src/styles/index.css`: стили для табеля, мобильный горизонтальный скролл.
- Backend:
  - Используется существующий `GET /api/timesheet/{object_id}` из I16.
- Тесты:
  - Frontend build и tests зелёные.

**Проверки:**
- `make test` → 57 passed.
- `make lint` → All checks passed!
- `npm run build` (frontend) → success.
- `npm test -- --run` (frontend) → 10 passed.

**Блокер/риск:**
- Нет.

**Следующий единственный шаг:**
- I18: Excel табеля.

**Изменённые файлы:**
- `max_daily_report/frontend/src/api/timesheet.ts` (new)
- `max_daily_report/frontend/src/pages/TimesheetPage.tsx`
- `max_daily_report/frontend/src/styles/index.css`
- `docs/max-mini-app-spec/PROGRESS.md`
