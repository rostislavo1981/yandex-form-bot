# PROGRESS

Обновлено: 2026-07-14.

## Текущий статус

I08 завершена. Добавлены чтение списка отчётов, статус сдачи и права по ролям.

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
| I09–I22 | WAIT | Выполняются строго по порядку |

## Текущая итерация: I09

Следующий агент делает только I09 из `08_implementation_plan.md`.

## Чек-лист I09

- [ ] Vite + React + TypeScript shell.
- [ ] React Router маршруты.
- [ ] API client (`axios`/`fetch`).
- [ ] MAX Bridge `window.maxBridge` + fallback.
- [ ] Backend verify initData + dev-only auth.
- [ ] TS build green.
- [ ] Unit tests официального validation vector.
- [ ] Обновлён `PROGRESS.md` и один коммит.

## HANDOFF NOTES

### 2026-07-14 — I08 завершена

**Агент:** kimi-k2.7-code:cloud  
**Ветка:** codex/i00-skeleton  
**Итерация:** I08 — Чтение и статус отчётов  
**Коммит:** `<TBD>`

**Сделано:**
- `app/services/report_service.py`:
  - `list_reports(...)` с фильтрами по дате, объекту, ответственному, пагинацией.
  - `submission_status(...)` возвращает `expected/submitted/late/pending/missing`.
  - Ролевая видимость: responsible видит только свои отчёты; manager/admin могут фильтровать по `responsible_user_id`.
- `app/api/reports.py`:
  - `GET /api/reports` — список отчётов.
  - `GET /api/reports/{id}` — детали отчёта (было, доработана схема).
  - `GET /api/submission-status?date=` — статус сдачи на дату.
- `app/main.py`:
  - Подключён `reports.submission_router`.
  - Dev middleware распространён на `/api/submission-status`.
- `app/schemas/reports.py`:
  - `ReportListResponse`, `SubmissionStatusResponse`, `MissingReportItem`.
- `tests/test_reports.py`:
  - Тест списка: responsible видит только свои отчёты.
  - Тест фильтра по дате.
  - Тест `submission-status`: `expected=2`, `pending=2`, после submit `submitted=1`.
- `tests/conftest.py`:
  - Truncate-список дополнен таблицами отчётов, obligations и outbox.

**Проверки:**
- `make test` → 37 passed.
- `make lint` → All checks passed!

**Блокер/риск:**
- Нет.

**Следующий единственный шаг:**
- I09: Frontend shell, React Router, API client, MAX Bridge, backend verify initData.

**Изменённые файлы:**
- `max_daily_report/app/api/reports.py`
- `max_daily_report/app/main.py`
- `max_daily_report/app/models/reports.py`
- `max_daily_report/app/schemas/reports.py`
- `max_daily_report/app/services/report_service.py`
- `max_daily_report/tests/conftest.py`
- `max_daily_report/tests/test_reports.py`
- `docs/max-mini-app-spec/PROGRESS.md`
