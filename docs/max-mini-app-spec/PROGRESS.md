# PROGRESS

Обновлено: 2026-07-14.

## Текущий статус

I11 завершена. EquipmentRows, персонал, валидация количеств.

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
| I12–I22 | WAIT | Выполняются строго по порядку |

## Текущая итерация: I12

Следующий агент делает только I12 из `08_implementation_plan.md`.

## Чек-лист I12

- [ ] WorkRows: вид работ, допустимый способ, единица, количество.
- [ ] Грунт, комментарий, submit.
- [ ] UUID Idempotency-Key на каждый submit.
- [ ] Экран успеха, защита от двойного submit.
- [ ] Обработка ошибок API с понятными сообщениями.
- [ ] Тесты и TS build зелёные.
- [ ] Обновлён `PROGRESS.md` и один коммит.

## HANDOFF NOTES

### 2026-07-14 — I11 завершена

**Агент:** kimi-k2.7-code:cloud  
**Ветка:** codex/i00-skeleton  
**Итерация:** I11 — Техника и персонал  
**Коммит:** `<TBD>`

**Сделано:**
- Frontend:
  - `frontend/src/components/EquipmentRows.tsx`: добавление/удаление строк, выбор типа техники через SearchSelect, принадлежность, количество.
  - `frontend/src/components/PersonnelField.tsx`: ИТР, штатные, внештатные с защитой от отрицательных значений.
  - `frontend/src/pages/ReportPage.tsx`: интегрированы персонал, техника, грунт, комментарий, кнопка отправить.
  - `frontend/src/api/catalogs.ts`: добавлены `searchEquipment`, `listUnits`.
  - `frontend/src/types/reports.ts`: `EquipmentRow`, `StaffValues`, `ReportFormData`.
  - Стили для карточек строк, кнопок, personnel grid.
- Тесты:
  - `frontend/src/test/EquipmentRows.test.tsx`: рендер пустого состояния.
  - `frontend/src/test/PersonnelField.test.tsx`: отрицательные значения не пропускаются.

**Проверки:**
- `make test` → 41 passed.
- `make lint` → All checks passed!
- `npm run build` (frontend) → success.
- `npm test` (frontend) → 9 passed.

**Блокер/риск:**
- Нет.

**Следующий единственный шаг:**
- I12: Работы и submit.

**Изменённые файлы:**
- `max_daily_report/frontend/src/components/EquipmentRows.tsx` (new)
- `max_daily_report/frontend/src/components/PersonnelField.tsx` (new)
- `max_daily_report/frontend/src/pages/ReportPage.tsx`
- `max_daily_report/frontend/src/api/catalogs.ts`
- `max_daily_report/frontend/src/types/reports.ts`
- `max_daily_report/frontend/src/types/catalogs.ts`
- `max_daily_report/frontend/src/styles/index.css`
- `max_daily_report/frontend/src/test/EquipmentRows.test.tsx` (new)
- `max_daily_report/frontend/src/test/PersonnelField.test.tsx` (new)
- `max_daily_report/frontend/package.json`
- `max_daily_report/frontend/package-lock.json`
- `docs/max-mini-app-spec/PROGRESS.md`
