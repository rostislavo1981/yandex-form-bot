# PROGRESS

Обновлено: 2026-07-15.

## Текущий статус

Статус `DOCKER QUALITY GATE PASSED`. Все автоматизируемые проверки O08 пройдены
в живом прогоне (ранее верифицированы только статически). Backend 179/179,
frontend 15/15, prod-build чистый. Следующий шаг — ручная приёмка через MAX
(docker-compose.phone.yml, R15).

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
| R15 | BLOCKED | Requires real MAX token/domain |
| R16 | COMPLETED | Object mapping, Docker DoD and Yandex Cloud plan |
| O00 | COMPLETED | Docker quality gate (test stages, docker-compose.test.yml) |
| O01 | COMPLETED | Contract model, ObjectContract, report snapshots |
| O02 | COMPLETED | ObjectMappings Excel import/export |
| O03 | COMPLETED | Object search by contract code/full_name |
| O04 | COMPLETED | Frontend contract selection in report form |
| O05 | COMPLETED | Report snapshots, contract validation |
| O06 | COMPLETED | Timesheet Excel with contract info |
| O07 | COMPLETED | Prod compose: migrations init, outbox scheduler |
| O08 | COMPLETED | Docker quality gate: all tests pass, builds clean |

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
- [ ] R15: Production acceptance (BLOCKED)
- [x] R16: Object mapping, Docker and Yandex Cloud plan
- [x] O00: Docker test stages, docker-compose.test.yml
- [x] O01: Contract model, ObjectContract, DailyReport snapshots
- [x] O02: ObjectMappings sheet in catalog Excel import/export
- [x] O03: Object search by contract code and full_name
- [x] O04: Frontend contract selection (auto/single/multiple)
- [x] O05: Report contract validation and snapshots
- [x] O06: Timesheet Excel with contract info
- [x] O07: Prod compose migrations init, outbox in scheduler
- [x] O08: Docker quality gate (179 backend + 15 frontend, builds clean, alembic check)

## HANDOFF NOTES

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
