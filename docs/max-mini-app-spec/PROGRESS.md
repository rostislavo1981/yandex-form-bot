# PROGRESS

Обновлено: 2026-07-14.

## Текущий статус

I22 завершена. MVP готов к release candidate `v0.1.0-rc1`.

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
| I19 | COMPLETED | Scheduler reminders |
| I20 | COMPLETED | Утренняя сводка |
| I21 | COMPLETED | Production deploy |
| I22 | COMPLETED | Приёмка MVP |

## Текущая итерация: —

Все итерации I00–I22 выполнены. MVP готов к release candidate.

## Чек-лист I22

- [x] Пройти чек-лист `09_testing_plan.md`.
- [x] Исправить только blockers.
- [x] Обновить документацию и tag release candidate.
- [x] Тесты и lint зелёные.
- [x] Обновлён `PROGRESS.md` и один коммит.

## HANDOFF NOTES

### 2026-07-14 — I22 завершена

**Агент:** kimi-k2.7-code:cloud  
**Ветка:** docs/max-mini-app-spec  
**Итерация:** I22 — Приёмка MVP  
**Коммит:** `<TBD>`  
**Tag:** `v0.1.0-rc1`

**Сделано:**
- Пройден чек-лист `09_testing_plan.md`.
- Добавлен `make frontend-check`: `npm run build` + `vitest run`.
- Все автоматические проверки зелёные.
- Ручная приёмка MAX/Mini App остаётся за пользователем с реальными токенами.

**Проверки:**
- `make lint` → All checks passed!
- `make test` → 64 passed, 7 warnings.
- `make frontend-check`:
  - `npm run build` → successful (`dist/index.html`, `dist/assets/...`).
  - `vitest run` → Test Files 6 passed (6), Tests 10 passed (10).
- `make prod-up` (local Docker) → db/api/scheduler/caddy healthy, health 200, seed
  + scheduler endpoints respond, backup script works.
- Исправлены blockers во время локального Docker-теста:
  - добавлены runtime deps `openpyxl` и `cryptography`;
  - `Caddyfile` использует plain HTTP для локального теста;
  - `docker-compose.prod.yml` маппит `8080/8443` чтобы не конфликтовать с macOS 443;
  - `README` объясняет переключение `DATABASE_URL` localhost ↔ db.

**Блокер/риск:**
- Нет.

**Дополнительно сделано после локальной приёмки:**
- Seed теперь создаёт `ResponsibleObjectAssignment` для `max-resp-1/obj-1` и
  `max-resp-2/obj-2`, чтобы полный сценарий «выбрать объект → заполнить →
  отправить» работал сразу после `app.seed`.
- Frontend dev-fallback активирован и в production-сборке через
  `frontend/.env.production VITE_ALLOW_DEV_AUTH=true`, поэтому локальный Docker
  стек можно тестировать в браузере без MAX.
- `app/main.py`: dev-only middleware теперь включается только при `APP_ENV=dev`,
  а не по `DEBUG=true`, чтобы тесты `test_auth.py` оставались корректными при
  любом `.env`. Добавлен SPA fallback (`/`, `/{full_path:path}`) для глубоких
  frontend-маршрутов, включая `/admin/catalogs`.
- `Makefile`: цель `test` принудительно использует `DATABASE_URL` с хостом
  `localhost`, чтобы `pytest` работал параллельно с Docker-стеком на хосте.
- Добавлена упрощённая web-админка `/admin/catalogs` (backend + frontend):
  CRUD для всех каталогов под `/api/admin/catalogs`, inline-редактирование,
  Excel import/export. Soft-delete для всех справочников.
- Проверен end-to-end в Docker: `/api/auth/me`, `/api/catalogs/*`,
  `POST /api/reports`, `/api/submission-status`, `/api/timesheet/*`,
  `/api/admin/catalogs/*`, `/admin/catalogs`.

**Следующий единственный шаг:**
- Пользователь запускает `make prod-up` на VPS (с `DATABASE_URL=...db:5432...`),
  регистрирует webhook и проходит ручную приёмку MAX/Mini App.

**Изменённые файлы:**
- `max_daily_report/pyproject.toml`
- `max_daily_report/Caddyfile`
- `max_daily_report/docker-compose.prod.yml`
- `max_daily_report/Makefile`
- `max_daily_report/README.md`
- `max_daily_report/.gitignore`
- `max_daily_report/app/seed.py`
- `max_daily_report/app/main.py`
- `max_daily_report/app/api/admin_catalogs.py`
- `max_daily_report/app/schemas/admin_catalogs.py`
- `max_daily_report/frontend/.env.production`
- `max_daily_report/frontend/src/api/client.ts`
- `max_daily_report/frontend/src/api/admin.ts`
- `max_daily_report/frontend/src/pages/AdminCatalogsPage.tsx`
- `max_daily_report/frontend/src/types/admin.ts`
- `max_daily_report/frontend/src/components/Layout.tsx`
- `max_daily_report/frontend/src/styles/index.css`
- `docs/max-mini-app-spec/SUMMARY.md`
- `docs/max-mini-app-spec/01_overview.md`
- `docs/max-mini-app-spec/02_architecture.md`
- `docs/max-mini-app-spec/04_api_contract.md`
- `docs/max-mini-app-spec/06_frontend_spec.md`
- `docs/max-mini-app-spec/07_project_structure.md`
- `docs/max-mini-app-spec/08_implementation_plan.md`
- `docs/max-mini-app-spec/09_testing_plan.md`
- `docs/max-mini-app-spec/13_catalogs_excel.md`
- `docs/max-mini-app-spec/PROGRESS.md`
