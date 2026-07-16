# 17. Yandex Cloud pilot runbook

Этот документ — пошаговый runbook для трека `YC00 → YC05` из
`16_object_mapping_docker_yandex_cloud.md`. Он дополняет Docker quality gate (O00–O08)
воспроизводимым развёртыванием пилота в Yandex Cloud. Локальная часть
(сборка image с immutable tag, проверка compose, документация) выполняется без
облачного аккаунта; шаги, требующие живого облака, помечены «требует YC».

Все команды выполняются из `max_daily_report/`.

## Актуальность

Дата: 2026-07-16. Тарифы/лимиты гранта проверять перед стартом в официальной
документации Yandex Cloud (ссылки в `16_object_mapping_docker_yandex_cloud.md`).

## Инварианты (уже выполнены в O00–O08)

- Один и тот же application image используется API, scheduler, worker, migrations
  (`docker-compose.prod.yml`, `target: base`).
- Outbox worker гарантирует доставку карточек (R04).
- Webhook регистрируется через `scripts/register_webhook.sh` (R03).
- Тесты изолированы в `mdr_test`, не трогают `mdr_db` (R00).

## DoD каждого YC-шага

1. Команда проверки записана и выполнена ровно для этого шага.
2. Нет изменений в бизнес-логике приложения — только инфраструктура/deploy.
3. `docker compose -f docker-compose.prod.yml config` проходит.
4. `docker compose -f docker-compose.test.yml run --rm backend-tests` зелёный
   (179 passed) перед любым cloud push.
5. Секреты не попадают в image или git (`.env` права `600`, `.gitignore`).

---

## YC00 — Платёжный аккаунт и защита от расходов  *(требует YC)*

Ручные действия в консоли Yandex Cloud:

1. Создать первый платёжный аккаунт, привязать карту (условие гранта).
2. Создать cloud/folder `mdr-pilot`.
3. Billing → Budgets: уведомления по фактической стоимости и остатку гранта
   (25%, 50%, 80%, 95%).

**DoD:** виден грант и дата окончания; уведомления подтверждены; вне `mdr-pilot`
нет ресурсов.

---

## YC01 — VM и сеть  *(требует YC)*

Создать Ubuntu LTS VM:

- 2 vCPU, уровень производительности 20%;
- 2 ГБ RAM (4 ГБ при OOM);
- 20 ГБ сетевого диска;
- 1 публичный IPv4;
- security group: `22/tcp` только с IP администратора, `80/443` из интернета;
- Docker Engine + Compose plugin.

```bash
# проверка после создания (с VM)
docker run --rm hello-world
timedatectl | grep "Time zone"   # должно быть Europe/Moscow
```

**DoD:** SSH только с разрешённого IP; лишние порты закрыты; `hello-world`
стартует; timezone корректна.

---

## YC02 — HTTPS-адрес  *(требует YC)*

Направить A-запись домена на публичный IP VM. Caddy (`Caddyfile`) автоматически
выпустит TLS через Let's Encrypt.

```bash
DOMAIN=mdr.example.com docker compose -f docker-compose.prod.yml up -d caddy
curl -fsS -o /dev/null -w "%{http_code}\n" https://mdr.example.com/api/health
```

**DoD:** `/api/health` → 200 по HTTPS; HTTP → редирект на HTTPS; сертификат
валиден с телефона.

---

## YC03 — Доставка application image

Локально собрать image с immutable tag = короткий SHA коммита, просканировать и
загрузить в Yandex Container Registry (YCR). На VM выполнять только pull +
миграция + запуск.

Используется `scripts/push_image.sh`:

```bash
export YCR_REGISTRY=cr.yandex/<registry-id>
./scripts/push_image.sh
# → собирает max-daily-report:<sha>, помечает latest, пушит, выводит digest
```

Команды эквивалентны:

```bash
TAG="$(git rev-parse --short HEAD)"
docker compose -f docker-compose.prod.yml build api
docker tag max_daily_report-api "cr.yandex/<registry-id>/mdr-api:${TAG}"
docker tag max_daily_report-api "cr.yandex/<registry-id>/mdr-api:latest"
docker push "cr.yandex/<registry-id>/mdr-api:${TAG}"
docker push "cr.yandex/<registry-id>/mdr-api:latest"
docker inspect --format='{{index .RepoDigests 0}}' "cr.yandex/<registry-id>/mdr-api:${TAG}"
```

**DoD:** digest локального и скачанного image совпадает; предыдущий tag
доступен для rollback; старые образы удаляются по политике реестра.

> Vulnerability scan в YCR выполняется автоматически после push; critical
> finding блокирует развёртывание.

---

## YC04 — Данные, секреты и запуск  *(требует YC)*

На VM:

```bash
# 1. .env с правами 600 (не в image/git)
install -m 600 /dev/null /opt/mdr/.env
# заполнить POSTGRES_PASSWORD, MAX_WEBHOOK_SECRET, INTERNAL_TOKEN (сильные, уникальные)

# 2. pull image по digest/tag
docker pull "cr.yandex/<registry-id>/mdr-api:${TAG}"

# 3. миграция + запуск (compose на VM использует тот же docker-compose.prod.yml)
DOMAIN=mdr.example.com ENV_FILE=/opt/mdr/.env \
  docker compose -f docker-compose.prod.yml up -d db
./scripts/migrate.sh
DOMAIN=mdr.example.com ENV_FILE=/opt/mdr/.env \
  docker compose -f docker-compose.prod.yml up -d

# 4. импорт проверенного Excel со справочниками через /admin/catalogs

# 5. webhook
MAX_BOT_TOKEN=... MAX_WEBHOOK_SECRET=... DOMAIN=mdr.example.com INTERNAL_TOKEN=... \
  ./scripts/register_webhook.sh

# 6. зашифрованный backup вне VM
./scripts/backup.sh && gpg -c backups/mdr_*.dump
```

**DoD:** контейнеры healthy; `/api/health` без initData → 200, `/api/*` без
валидного `X-Init-Data` → 401; internal endpoint без токена → 401; webhook
зарегистрирован; backup восстанавливается в отдельную test-БД через
`scripts/restore-smoke.sh`.

---

## YC05 — Облачная приёмка  *(требует YC)*

Повторить матрицу O08 через облачный URL, плюс:

- остановить/запустить API — данные сохраняются;
- остановить worker, создать отчёт, запустить worker — карточка приходит 1 раз;
- все 4 расписания по Москве выполнились;
- Billing через 24ч — записать расход гранта и прогноз до конца 60 дней.

**DoD:** один ответственный сдаёт отчёты по двум объектам с телефона; группа
получает карточки и утреннюю сводку; табель и Excel сходятся; rollback
проверен (`docker compose` на предыдущем tag).

---

## Порядок

`YC00 → YC01 → YC02 → YC03 → YC04 → YC05`. YC03 частично выполним локально
(сборка + push при наличии YCR-доступа). YC00/YC01/YC02/YC04/YC05 требуют живого
облачного аккаунта и выполняются вами.
