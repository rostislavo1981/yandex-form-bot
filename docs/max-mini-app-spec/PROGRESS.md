# PROGRESS

Обновлено: 2026-07-16.

## Текущий статус

Статус `LOCAL RELEASE CANDIDATE READY`. Backend 184/184, frontend 16/16,
Ruff, Alembic и production build чистые. Production-smoke проверен вместе с
отдельным worker, scheduler, ежедневным backup и восстановлением дампа.
Телефонный стенд поднят, реальный Excel импортирован, webhook MAX указывает на
живой HTTPS tunnel. Осталась только ручная проверка кнопок/формы пользователем
в MAX и назначение реальных ответственных на объекты.

| Итерация | Статус | Результат |
|---|---|---|
| I00–I22 | COMPLETED | MVP skeleton + features |
| R00 | COMPLETED | Test DB isolation (mdr_test) |
| R01 | COMPLETED | MAX REST client aligned with official API |
| R02 | COMPLETED | Webhook parses official MAX updates |
| R03 | COMPLETED | Production HTTPS/443, preflight, webhook registration |
| R04 | COMPLETED | Reliable outbox worker with exponential backoff |
| R05 | COMPLETED | All MAX control buttons visible and working |
| R06 | COMPLETED | Dynamic units validated |
| R07 | COMPLETED | Contractor search endpoint |
| R08 | COMPLETED | One report per obligation, FOR UPDATE |
| R09 | COMPLETED | Reports and Status pages implemented |
| R10 | COMPLETED | Per-day status in timesheet |
| R11 | COMPLETED | Full catalog Excel round-trip |
| R12 | COMPLETED | Timesheet Excel with day_status styling |
| R13 | COMPLETED | CI with backend/frontend/docker jobs |
| R14 | COMPLETED | Input validation hardening |
| R15 | IN PROGRESS | Phone stand + webhook ready; manual MAX taps remain |
| R16 | COMPLETED | Object mapping, Docker DoD and Yandex Cloud plan |
| O00 | COMPLETED | Docker quality gate (test stages, docker-compose.test.yml) |
| O01 | COMPLETED | Contract model, ObjectContract, report snapshots |
| O02 | COMPLETED | ObjectMappings Excel import/export |
| O03 | COMPLETED | Object search by contract code/full_name |
| O04 | COMPLETED | Frontend contract selection in report form |
| O05 | COMPLETED | Report snapshots, contract validation |
| O06 | COMPLETED | Timesheet Excel with contract info |
| O07 | COMPLETED | Prod compose: migrations, separate worker, scheduler, backup |
| O08 | COMPLETED | Docker gate + live prod/restore smoke pass |

## Чек-лист

- [x] R00: Test DB guard, mdr_test created
- [x] R01: MAX client uses query params, answer_callback
- [x] R02: Webhook uses X-Max-Bot-Api-Secret, update_type
- [x] R03: Production ports 80/443, preflight
- [x] R04: Exponential backoff, FOR UPDATE SKIP LOCKED
- [x] R05: All buttons have handlers
- [x] R06: Dynamic units validated
- [x] R07: Contractor search endpoint
- [x] R08: Idempotency, duplicate rejection
- [x] R09: ReportsPage, StatusPage
- [x] R10: day_status in timesheet
- [x] R11: Users/Assignments Excel
- [x] R12: Timesheet Excel styling
- [x] R13: GitHub Actions CI
- [x] R14: Comment max_length
- [ ] R15: Manual acceptance in MAX (stand and webhook are ready)
- [x] R16: Object mapping, Docker and Yandex Cloud plan
- [x] O00: Docker test stages, docker-compose.test.yml
- [x] O01: Contract model, ObjectContract, DailyReport snapshots
- [x] O02: ObjectMappings sheet in catalog Excel import/export
- [x] O03: Object search by contract code and full_name
- [x] O04: Frontend contract selection (auto/single/multiple)
- [x] O05: Report contract validation and snapshots
- [x] O06: Timesheet Excel with contract info
- [x] O07: Prod compose migrations init, separate outbox worker, scheduler, backup
- [x] O08: Docker quality gate (184 backend + 16 frontend, builds clean, alembic check, restore smoke)

## HANDOFF NOTES

### 2026-07-16 — release-candidate hardening and live phone stand

**Ветка:** `codex/i00-skeleton`

**Сделано:**
- реальный формат файла «СПИСОК объектов…xlsx» распознаётся по заголовку
  `краткое название`, преобразуется в Objects/ObjectMappings и больше не может
  пройти как пустой no-op;
- короткое имя применяется к объекту, длинные названия хранятся как договоры;
- при нескольких договорах выбор обязателен и на frontend, и на backend;
- «Кто не сдал» учитывает отсутствующие, pending и missed обязательства;
- импорт ограничен 10 МБ и сериализован advisory-lock от параллельной гонки;
- добавлены `/api/ready`, отдельный outbox worker и production backup с
  restore-smoke;
- CI запускает реальные миграции и DB-aware readiness smoke;
- phone compose сам запускает миграции, activation script получает tunnel и
  регистрирует webhook;
- предоставленный Excel применён в изолированной phone DB: 38 новых объектов,
  37 уникальных длинных названий, 38 рабочих связей; две служебные ячейки
  `??`/`нет пока договора` пропущены.

**Проверки:**
- backend Docker: **184 passed**;
- frontend Docker: **16 passed**, production build OK;
- Ruff, `git diff --check`, compose config и `alembic check`: OK;
- production live smoke: migrations exit 0, API/worker/scheduler/backup healthy;
- custom-format backup создан и успешно восстановлен во временную DB;
- phone HTTPS `/api/ready`: OK; webhook виден в MAX subscriptions с полным
  набором событий.

**Осталось вручную (R15):**
- установить текущий tunnel URL как Mini App URL в кабинете MAX;
- открыть бота/группу, нажать все видимые кнопки и отправить один отчёт;
- после регистрации реальных пользователей назначить им объекты через админку
  или полный Excel Users/Assignments.

### 2026-07-16 — YC track: local runbook + push script (YC03 prep)

**Агент:** Kilo (kilo-auto/free)
**Ветка:** codex/i00-skeleton
**Итерация:** YC03 (подготовка) — доставка image в Yandex Container Registry
**Коммит:** см. ниже

**Сделано:**
- `docs/max-mini-app-spec/17_yandex_cloud_runbook.md` — runbook YC00–YC05 с
  командами, DoD и разделением «требует YC» / локально-выполнимое
- `max_daily_report/scripts/push_image.sh` — сборка image с immutable SHA-тегом,
  push в YCR, вывод digest для rollback (YC03)

**Не сделано:**
- YC00/YC01/YC02/YC04/YC05 — требуют живого облачного аккаунта (вне окружения)
- реальный `docker push` в YCR — требует `docker login` в registry

**Проверки:**
- `sh -n scripts/push_image.sh` → syntax OK
- `docker compose -f docker-compose.prod.yml config` → valid (exit 0)
- prod build (api/scheduler/migrations) пройден ранее в O08 live run

**Blocker/риск:**
- облачный deploy требует YC-аккаунт, домен и YCR-доступ — только пользователь

**Следующий единственный шаг:**
- YC03: при наличии YCR `export YCR_REGISTRY=... && ./scripts/push_image.sh`

**Изменённые файлы:**
- docs/max-mini-app-spec/17_yandex_cloud_runbook.md (новый)
- max_daily_report/scripts/push_image.sh (новый)

### 2026-07-16 — O08 Docker quality gate (live run)

**Агент:** Kilo (kilo-auto/free)
**Ветка:** codex/i00-skeleton
**Итерация:** O08 — полная локальная приёмка (живой прогон Docker)
**Коммит:** нет (только docs/PROGRESS.md)

**Сделано:**
- Запущены в реальном Docker все отложенные команды качества из `16_object_mapping_docker_yandex_cloud.md` (ранее заблокированы в sandbox)
- `docker compose -f docker-compose.test.yml config` — valid (exit 0)
- `docker compose -f docker-compose.prod.yml config` — valid (exit 0)
- `docker compose -f docker-compose.phone.yml config` — valid (exit 0)
- `backend-tests` stage собран и прогнан: **179 passed**
- `frontend-tests` stage собран и прогнан: **15 passed** + production build clean (dist 273 kB)
- `docker compose -f docker-compose.prod.yml build` — api/scheduler/migrations собраны

**Не сделано:**
- R15 ручная приёмка через MAX (требует реальный `MAX_BOT_TOKEN`, домен, webhook secret, тест-группу) — заблокирована, вне окружения
- Phone-stand команды (`.env.phone` с токеном) — заблокированы отсутствием creds

**Проверки:**
- `docker compose -f docker-compose.test.yml run --rm backend-tests` → 179 passed, 23.8s
- `docker compose -f docker-compose.test.yml run --rm frontend-tests` → 15 passed + build OK
- `docker compose -f docker-compose.prod.yml config` / `build` → OK

**Blocker/риск:**
- R15 требует реальных MAX-учёток и домена; невыполнимо без пользователя

**Следующий единственный шаг:**
- R15: при наличии `MAX_BOT_TOKEN`/`MAX_GROUP_ID`/домена развернуть phone-stand и пройти ручную матрицу из O08 (10 пунктов)

**Изменённые файлы:**
- docs/max-mini-app-spec/PROGRESS.md

### 2026-07-15 — O00–O07 complete

**Агент:** MiMoCode
**Ветка:** codex/i00-skeleton

**Сделано:**
- O00: Docker test stages (backend-test, frontend-test), docker-compose.test.yml
- O01: Contract/ObjectContract models, DailyReport snapshots, migration
- O02: ObjectMappings sheet in Excel import/export with validation
- O03: Object search by contract code/full_name, ObjectItem schema
- O04: Frontend contract selection (auto/single/multiple)
- O05: Report contract validation, foreign/inactive rejection
- O06: Timesheet Excel with contract info
- O07: Migrations init container, outbox processing in scheduler

**Проверки:**
- 179 backend tests pass (Docker + local)
- 15 frontend tests pass (Docker + local)
- ruff clean
- Frontend builds
- docker-compose.prod.yml config valid
- docker-compose.test.yml config valid
- docker-compose.phone.yml config valid
- alembic check passes
- Production image: no tests, no pytest, frontend static included

**Blocker:**
- R15 requires real MAX token, domain, webhook secret, test group
- Phone test stand requires MAX_BOT_TOKEN in .env.phone

**Следующий шаг:**
- Ручная приёмка через docker-compose.phone.yml (O08 manual matrix)
