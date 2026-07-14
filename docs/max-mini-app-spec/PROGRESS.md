# PROGRESS

Обновлено: 2026-07-14.

## Текущий статус

I09 завершена. Создан frontend shell, backend проверка initData, dev-only auth, unit tests.

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
| I10–I22 | WAIT | Выполняются строго по порядку |

## Текущая итерация: I10

Следующий агент делает только I10 из `08_implementation_plan.md`.

## Чек-лист I10

- [ ] `SearchSelect` компонент: debounce, серверный поиск, состояния loading/empty/error.
- [ ] Поля объекта, этапа, даты, ответственного, contractor.
- [ ] Смена объекта очищает этап; этапы только для выбранного объекта.
- [ ] Responsible видит только назначенные объекты.
- [ ] Mobile smoke.
- [ ] Тесты и TS build зелёные.
- [ ] Обновлён `PROGRESS.md` и один коммит.

## HANDOFF NOTES

### 2026-07-14 — I09 завершена

**Агент:** kimi-k2.7-code:cloud  
**Ветка:** codex/i00-skeleton  
**Итерация:** I09 — Frontend shell, MAX Bridge, initData verify  
**Коммит:** `<TBD>`

**Сделано:**
- Frontend (`frontend/`):
  - Vite + React + TypeScript strict shell.
  - React Router: `/report`, `/reports`, `/timesheet`, `/status`.
  - Mobile-first CSS, ширина до 640 px.
  - API client с `X-Init-Data` header и dev fallback под флагом `VITE_ALLOW_DEV_AUTH=true`.
  - MAX Bridge wrapper (`window.WebApp.initData`, `ready()`, `close()`, `expand()`).
  - `useAuth` hook вызывает `GET /api/auth/me` и рендерит Layout/Loading/Error.
  - Vitest + jsdom + `@testing-library/react` unit tests.
- Backend:
  - `app/api/auth.py`: `GET /api/auth/me` с валидацией MAX initData по HMAC-SHA256.
  - Проверка `auth_date` TTL (default 1 час).
  - Dev-only fallback `X-Init-Data: dev` только при `DEBUG=true` или `APP_ENV=dev`.
  - `app/main.py`: dev middleware распространён на все `/api/*` кроме health; подключён `auth.router`.
  - `app/config.py`: добавлен `app_env`.
  - `app/schemas/users.py`: `UserResponse`.
- Тесты:
  - `tests/test_auth.py`: dev header, invalid signature, valid signature, expired initData.
  - `frontend/src/test/Layout.test.tsx`: рендер Layout, роль manager показывает Status.
  - `frontend/src/test/auth.test.ts`: client отправляет `X-Init-Data`, ошибки API пробрасываются.

**Проверки:**
- `make test` → 41 passed.
- `make lint` → All checks passed!
- `npm run build` (frontend) → success.
- `npm test` (frontend) → 5 passed.

**Блокер/риск:**
- Нет.

**Следующий единственный шаг:**
- I10: SearchSelect и основные поля формы.

**Изменённые файлы:**
- `max_daily_report/app/api/auth.py` (new)
- `max_daily_report/app/config.py`
- `max_daily_report/app/main.py`
- `max_daily_report/app/schemas/users.py` (new)
- `max_daily_report/.env.example`
- `max_daily_report/.env`
- `max_daily_report/tests/test_auth.py` (new)
- `max_daily_report/frontend/**` (new)
- `docs/max-mini-app-spec/PROGRESS.md`
