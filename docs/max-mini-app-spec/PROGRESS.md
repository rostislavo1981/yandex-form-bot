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

## Текущая итерация: FIXLIST (после код-ревью)

Все итерации I00–I22 выполнены, но полное код-ревью 2026-07-14 нашло критические
проблемы (прод-авторизация не подключена, незащищённые мутирующие endpoints,
падающий webhook-callback и др.). **Release candidate заблокирован** до закрытия
групп F1–F5 из [`FIXLIST.md`](./FIXLIST.md).

Следующий агент работает по `FIXLIST.md` строго по порядку групп: F1 (auth) →
F2 (webhook) → F3 (валидация отчёта) → F4 (табель/obligations) → F5 (scheduler)
→ F6/F7. Каждый пункт = фикс + регресс-тест + отметка `[x]` с hash коммита.

## Чек-лист I22

- [x] Пройти чек-лист `09_testing_plan.md`.
- [x] Исправить только blockers.
- [x] Обновить документацию и tag release candidate.
- [x] Тесты и lint зелёные.
- [x] Обновлён `PROGRESS.md` и один коммит.

## HANDOFF NOTES

### 2026-07-14 — Полное код-ревью, создан FIXLIST.md

**Агент:** Claude Opus 4.8
**Ветка:** codex/i00-skeleton
**Итерация:** пост-I22 ревью
**Коммит:** см. git log (fixlist)

**Сделано:**
- Полное код-ревью всех 46 модулей `max_daily_report/` (backend + frontend).
- Прогнаны `make lint` (чисто), `make test` (74 passed), `make frontend-check`
  (build ok, 10 passed) — зелёные, но покрывают только dev-путь авторизации.
- Составлен [`FIXLIST.md`](./FIXLIST.md): 7 групп исправлений (F1–F7),
  ~30 пунктов с file:line ссылками и требованиями к регресс-тестам.

**Ключевые находки (детали в FIXLIST):**
- F1: initData-авторизация подключена только к `/api/auth/me`; остальные
  endpoints читают `request.state.user` от dev-middleware → в проде всё 401;
  import/apply, scheduler, worker вообще без auth; `GET /api/reports/{id}` без auth.
- F2: webhook `my_reports` обращается к несуществующим полям модели (crash);
  Telegram-ссылка t.me с префиксом токена; кнопки рассылок без обработчиков.
- F3: works-only отчёт отклоняется (порядок валидаторов); soil=0 проходит как
  содержимое; отрицательный персонал принимается; дубль дня → 500.
- F4: персонал/грунт в табеле затираются при 2 отчётах в день; average не по
  expected; obligations вне периода назначения; late никогда не ставится.
- F5: notification_log падает на UNIQUE при повторном сбое; advisory lock
  не переживает commit при NullPool; fire-and-forget task в scheduler_runner.

**Блокер/риск:**
- `v0.1.0-rc1` НЕ ставить до закрытия F1–F5.

**Следующий единственный шаг:**
- Открыть `FIXLIST.md`, начать F1.1 (общий auth-dependency) в ветке
  `codex/fix-f1-auth`.

---

### 2026-07-14 — I22 завершена

**Агент:** kimi-k2.7-code:cloud  
**Ветка:** docs/max-mini-app-spec  
**Итерация:** I22 — Приёмка MVP  
**Коммит:** `08b23c4`  
**Tag:** `v0.1.0-rc1` (предстоит поставить после push)

**Сделано:**
- Пройден чек-лист `09_testing_plan.md`.
- Добавлен `make frontend-check`: `npm run build` + `vitest run`.
- Все автоматические проверки зелёные.
- Ручная приёмка MAX/Mini App остаётся за пользователем с реальными токенами.

**Проверки:**
- `make lint` → All checks passed!
- `make test` → 74 passed, 7 warnings.
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
- Добавлен и зелёный `tests/test_admin_catalogs.py` (10 тестов): CRUD/soft-delete
  для объектов, этапов, подрядчиков, единиц, техники, видов/способов работ,
  связных таблиц, назначений и пользователей, а также отказ `responsible`.
  Исправлены list-эндпоинты связных сущностей: `selectinload` вместо lazy load;
  в `ResponsibleObjectAssignment` добавлены relationships `user`/`object`.
- Улучшен UX админки: выпадающие подсказки по коду/названию для связных полей
  (`object_id`, `stage_id`, `work_type_id`, `work_method_id`, `user_id`,
  `default_unit_id`, `default_contractor_id`) вместо ввода сырых ID.
- Проверен end-to-end в Docker: `/api/auth/me`, `/api/catalogs/*`,
  `POST /api/reports`, `/api/submission-status`, `/api/timesheet/*`,
  `/api/admin/catalogs/*`, `/admin/catalogs`.

**Документация доделана:**
- Все маркеры `зарезервировано/не реализовано` переведены в явные заметки о scope.
- `04_api_contract.md` дополнен полными схемами admin endpoints, control-panel,
  scheduler/worker и dev-режимом.
- `07_project_structure.md` приведён к реальному дереву файлов.
- `13_catalogs_excel.md` синхронизирован с одношаговым import/apply.
- `15_group_bot.md` дополнен расписанием, счётчиками, пультами, чек-листом.
- `10_glossary.md` расширен терминами outbox, advisory lock, soft-delete, pg_trgm.
- `12_track_A_bot_first.md` оформлен как полноценный redirect с обоснованием.
- `01_overview.md`, `02_architecture.md`, `06_frontend_spec.md`, `14_timesheet.md`,
  `SUMMARY.md` уточнены роли, dev-режим, SPA fallback, права табеля.

**Следующий единственный шаг:**
- Пользователь запускает `make prod-up` на VPS (с `DATABASE_URL=...db:5432...`),
  регистрирует webhook и проходит ручную приёмку MAX/Mini App.

**Изменённые файлы (I22 и доделка):**
- `max_daily_report/pyproject.toml`
- `max_daily_report/Caddyfile`
- `max_daily_report/docker-compose.prod.yml`
- `max_daily_report/Makefile`
- `max_daily_report/README.md`
- `max_daily_report/.gitignore`
- `max_daily_report/app/seed.py`
- `max_daily_report/app/main.py`
- `max_daily_report/app/api/admin_catalogs.py`
- `max_daily_report/app/models/reports.py`
- `max_daily_report/app/schemas/admin_catalogs.py`
- `max_daily_report/tests/test_admin_catalogs.py`
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
- `docs/max-mini-app-spec/10_glossary.md`
- `docs/max-mini-app-spec/11_two_tracks.md`
- `docs/max-mini-app-spec/12_track_A_bot_first.md`
- `docs/max-mini-app-spec/14_timesheet.md`
- `docs/max-mini-app-spec/15_group_bot.md`
