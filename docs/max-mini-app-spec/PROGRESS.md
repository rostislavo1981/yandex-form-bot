# PROGRESS

Обновлено: 2026-07-15.

## Текущий статус

Статус `REMEDIATION COMPLETE`. Все итерации R00–R14 выполнены.
R15 (production acceptance) заблокирован без реального MAX токена/домена.

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
| R16 | IN_PROGRESS | Documentation update |

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
- [ ] R16: Final docs sync

## HANDOFF NOTES

### 2026-07-15 — REMEDIATION R00–R14 complete

**Агент:** MiMoCode
**Ветка:** codex/i00-skeleton
**Коммиты:** 1cc8248 (R00), fc1c5cf (R01+R02), bf55919 (R03), 2461c4f (R04), 032c25b (R05), 8550b5b (R06), 0793fe8 (R07), de9813f (R08), ae4cc97 (R09), a1b2861 (R10), e45a06a (R11), 7f832e8 (R12), 199b38a (R13), bf2208c (R14)

**Сделано:**
- R00: Test DB isolation with guard
- R01+R02: MAX client and webhook aligned with official API
- R03: Production HTTPS/443, preflight validation
- R04: Exponential backoff, FOR UPDATE SKIP LOCKED
- R05: All MAX control buttons working
- R06: Dynamic units validated
- R07: Contractor search endpoint
- R08: One report per obligation
- R09: ReportsPage and StatusPage
- R10: Per-day status in timesheet
- R11: Full catalog Excel round-trip
- R12: Timesheet Excel styling
- R13: GitHub Actions CI
- R14: Input validation hardening

**Проверки:**
- 151 backend tests pass
- 10 frontend tests pass
- ruff clean
- Frontend builds

**Blocker:**
- R15 requires real MAX token, domain, webhook secret, test group

**Следующий шаг:**
- R15: Production acceptance with real MAX credentials
