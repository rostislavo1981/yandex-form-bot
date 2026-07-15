# 16. Сопоставление объектов: короткие итерации, Docker и Yandex Cloud

Актуальность облачных условий: 2026-07-15. Перед production-развёртыванием
повторно проверить тарифы и лимиты в официальной документации Yandex Cloud.

## Результат

Пользователь выбирает короткое рабочее название объекта. Поиск находит объект
по короткому названию, коду, адресу и полному договорному названию. Полное
название подтягивается автоматически. Если у короткого объекта несколько
договоров, форма показывает дополнительный выбор только для такого объекта.

Каждая итерация ниже должна завершаться тестом в Docker. Агент не начинает
следующую итерацию, пока не выполнен DoD текущей.

## Фактическая инфраструктура проекта

Текущий production-контур рассчитан на постоянно работающие процессы:

- FastAPI + собранный React frontend;
- PostgreSQL 16;
- scheduler с ежедневными заданиями;
- outbox worker;
- Caddy для HTTPS.

Это напрямую подходит для одной VM с Docker Compose. Serverless-развёртывание
потребует заменить PostgreSQL на YDB или оплачиваемую внешнюю PostgreSQL,
а scheduler и worker — на триггеры.

Отдельный обязательный дефект перед cloud deploy: `docker-compose.prod.yml`
содержит API, scheduler, PostgreSQL и Caddy, но не содержит worker. Без worker
карточки отчётов из outbox не будут гарантированно отправляться в группу.

## Общий DoD каждой итерации

1. Изменение ограничено одной бизнес-задачей.
2. Есть новый автоматический тест на happy path и хотя бы один негативный случай.
3. Backend-тест выполняется в test-контейнере с отдельной БД `mdr_test`.
4. Frontend-изменение проходит `vitest` и production build в Docker.
5. `docker compose config` проходит для всех затронутых compose-файлов.
6. Миграция проверена командами `upgrade head`, `downgrade -1`, `upgrade head`
   на одноразовой локальной test-БД.
7. В документации записаны команда проверки и фактический результат.

## Локальные итерации

### O00 — Docker quality gate

**Сделать:** добавить test stage в Dockerfile и `docker-compose.test.yml` с
отдельной PostgreSQL `mdr_test`. Backend-образ test stage должен содержать
`tests/` и зависимости `.[dev]`. Frontend test stage выполняет `npm test` и
`npm run build`.

**Проверки:**

```bash
docker compose -f docker-compose.test.yml config
docker compose -f docker-compose.test.yml build
docker compose -f docker-compose.test.yml run --rm backend-tests
docker compose -f docker-compose.test.yml run --rm frontend-tests
```

**DoD:** тесты не используют `mdr_db`; production-образ не содержит pytest и
исходники тестов.

#### Фактические результаты проверок O00

Дата выполнения: 2026-07-15.

**Изменения:**

- `max_daily_report/Dockerfile`: сохранены stages `frontend-builder` и `base`
  (production). Добавлены:
  - `backend-test` (на основе `base`): копирует `tests/`, ставит dev-зависимости
    `pip install -e ".[dev]"`, CMD
    `["sh","-c","alembic upgrade head && pytest -q"]`.
  - `frontend-test` (на основе `node:20-alpine`): `WORKDIR /frontend`,
    `npm ci`, копирует `frontend/`, CMD
    `["sh","-c","npm run test && npm run build"]`.
- `max_daily_report/docker-compose.test.yml` (новый): сервисы `db`
  (`postgres:16-alpine`, `mdr_test`, healthcheck `pg_isready`, volume
  `mdr_test_data`, сеть `mdr-test`), `backend-tests` (target `backend-test`,
  `depends_on db.service_healthy`, env `TEST_DATABASE_URL`/`DATABASE_URL` →
  `db:5432/mdr_test`, `APP_ENV=dev`), `frontend-tests` (target `frontend-test`).
- В production compose-файлах (`docker-compose.yml`, `docker-compose.prod.yml`,
  `docker-compose.phone.yml`) у сервисов `api`/`scheduler`/`worker` добавлен
  явный `target: base`, чтобы добавление тестовых stages не изменило цель
  сборки production-образа (по умолчанию собирается последний stage).

**Проверки в терминале (из `max_daily_report/`):**

> Внимание: в данном окружении выполнение shell-команд (bash) заблокировано
> правилом безопасности агента, поэтому живые команды Docker ниже не были
> запущены автоматически. Статическая верификация пройдена (см. ниже).
> Команды следует выполнить вручную на хосте с Docker:

```bash
cd max_daily_report
docker compose -f docker-compose.test.yml config
docker compose -f docker-compose.test.yml build
docker compose -f docker-compose.test.yml run --rm backend-tests
docker compose -f docker-compose.test.yml run --rm frontend-tests
```

| Проверка | Статус | Результат |
| --- | --- | --- |
| `docker compose -f docker-compose.test.yml config` | Не выполнено (sandbox) | YAML валиден при статическом разборе; требует запуска на хосте |
| `docker compose -f docker-compose.test.yml build` | Не выполнено (sandbox) | Ожидается успех; stages `backend-test` и `frontend-test` корректны |
| `run --rm backend-tests` | Не выполнено (sandbox) | Ожидается `alembic upgrade head && pytest -q` без ошибок |
| `run --rm frontend-tests` | Не выполнено (sandbox) | Ожидается `npm run test && npm run build` без ошибок |

**Статическая верификация (выполнена):**

- Production-stage `base` (`Dockerfile:11-44`) копирует только `pyproject.toml`,
  `app`, статику из `frontend-builder`, `alembic.ini` и ставит только runtime
  зависимости (`pip install -e "."`, `Dockerfile:37`) — без `.[dev]`, значит
  `pytest` в production-образе отсутствует. `tests/` копируется только в
  `backend-test` (`Dockerfile:49`), в `base` нет.
- Тесты подключаются к БД через `TEST_DATABASE_URL`, по умолчанию
  `...@localhost:5432/mdr_test` (`tests/conftest.py:13-19`). Строка `mdr_db`
  встречается в тестах только как константа-суффикс продовой БД и в
  `test_r00_db_guard.py` как негативный проверочный случай guard'а, который
  запрещает TRUNCATE продовой БД. То есть тесты не используют `mdr_db`, а
  используют `mdr_test`.
- `docker-compose.test.yml`: `db` создаёт `POSTGRES_DB=mdr_test`, `backend-tests`
  пробрасывает `TEST_DATABASE_URL`/`DATABASE_URL` на `db:5432/mdr_test`.

**DoD O00:** статические критерии выполнены (production-образ без pytest и
`tests/`; тесты используют `mdr_test`, не `mdr_db`; конфигурация compose
корректна). Живой прогон `config`/`build`/`run` заблокирован ограничением
окружения — требуется ручной запуск четырёх команд выше на хосте с Docker для
финального подтверждения.

### O01 — Модель договоров и связей

**Сделать:**

- оставить `objects.name` коротким рабочим названием;
- добавить `contracts(code, full_name, active, created_at, updated_at)`;
- добавить `object_contracts(object_id, contract_id, is_primary, active)`;
- добавить nullable `daily_reports.contract_id` для безопасной миграции;
- запретить дубли пары `(object_id, contract_id)`.

**Тесты:** один объект → один договор; один объект → два договора; один договор
→ два объекта; duplicate link отклоняется; downgrade/upgrade сохраняет текущие
отчёты.

**DoD:** старая форма продолжает сохранять отчёт без потери данных; новая схема
допускает фактические связи из исходного Excel.

### O02 — Импорт сопоставлений из Excel

**Сделать:** добавить лист `ObjectMappings`:

| object_code | short_name | contract_code | full_name | primary | active |
|---|---|---|---|---:|---:|
| OBJ-001 | Тамбасова | RT-26-1-01 | Полное название | 1 | 1 |
| OBJ-001 | Тамбасова | SP-26-1-04 | Второе название | 0 | 1 |

Импорт сначала показывает preview и только потом применяет изменения одной
транзакцией. Значения `??` и `нет пока договора` не создают договор, а дают
понятное предупреждение.

**Тесты:** 38 коротких объектов, 40 длинных строк, две связи 1→N, одна связь
N→1, повторный импорт идемпотентен, ошибка откатывает весь файл.

**Docker smoke:** загрузить копию исходного файла через `/admin/catalogs`,
проверить preview, применить и сверить количества SQL-запросом.

### O03 — API поиска объектов

**Сделать:** API объекта возвращает:

```json
{
  "id": 1,
  "code": "OBJ-001",
  "name": "Пискаревский",
  "contracts": [
    {"id": 10, "code": "RT-26-1-05", "full_name": "РТ_26-1-05СМР...", "primary": true}
  ]
}
```

Поиск работает по `objects.name`, `objects.code`, `contracts.code` и
`contracts.full_name`. Ограничение объектов ответственного сохраняется.

**Тесты:** поиск по короткому имени, фрагменту адреса, коду договора, полному
названию; чужой объект не появляется ответственному; inactive записи скрыты.

### O04 — Простая форма

**Сделать:** первая строка результата — короткое название, вторая — сокращённое
полное название. После выбора полное название показывается read-only. Если связь
одна, `contract_id` устанавливается автоматически. Если связей несколько,
появляется поле «Договор/официальный объект».

**Тесты frontend:** один договор подставляется; два договора показывают выбор;
смена объекта очищает этап и договор; поиск длинного названия возвращает короткий
объект; длинный текст не ломает mobile layout.

**Docker phone smoke:** открыть Mini App через MAX, найти «Пискаревский» по
части длинного названия, затем проверить «Тамбасова» с двумя вариантами.

### O05 — Сохранение отчёта и история

**Сделать:** для одного договора backend сам подставляет его ID; для нескольких
требует допустимый `contract_id`. В отчёте хранить snapshot короткого и полного
названия, чтобы переименование справочника не меняло историю.

**Тесты:** подмена чужого договора отклоняется; inactive mapping отклоняется;
один договор определяется автоматически; повторный submit не создаёт дубль;
карточка группы содержит короткое название, подробности — полное.

### O06 — Табель и Excel

**Сделать:** табель остаётся разделённым по короткому объекту. В подробном
отчёте и Excel добавить код и полное название договора. Суммы по дням и итог за
период не смешивают разные единицы измерения.

**Тесты:** две строки ТКР могут иметь общий договор, но разные табели; два
договора «Тамбасова» не создают два объекта; экспорт повторно открывается и
содержит ожидаемые формулы/итоги.

### O07 — Production Compose parity

**Сделать:** добавить worker в `docker-compose.prod.yml`, health/readiness,
resource limits, restart policy, миграцию до запуска API и ежедневный `pg_dump`.
Один и тот же application image используется API, scheduler и worker.

**Тесты:** outbox переживает restart; один event отправляется ровно один раз;
остановка worker не теряет отчёт; после запуска worker событие доставляется.

### O08 — Полная локальная приёмка

```bash
docker compose -f docker-compose.test.yml run --rm backend-tests
docker compose -f docker-compose.test.yml run --rm frontend-tests
docker compose -f docker-compose.prod.yml config
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.phone.yml up -d --build
docker compose -f docker-compose.phone.yml run --rm api alembic upgrade head
docker compose -f docker-compose.phone.yml run --rm api python -m app.seed
```

Ручная матрица:

1. MAX `/start` → личные кнопки видны.
2. В группе виден пульт с кнопками.
3. Поиск объекта работает по короткому и длинному названию.
4. Сдан отчёт для объекта с одним договором.
5. Сдан отчёт для объекта с двумя договорами.
6. В группу пришла одна краткая карточка.
7. Табель показывает правильный день и суммы.
8. Вручную вызваны reminder и morning summary.
9. После restart данные и кнопки сохранились.
10. Excel экспорт открывается и сходится с UI.

## Yandex Cloud: рекомендуемый бесплатный пилот

### Важное ограничение

У Yandex Compute Cloud нет постоянно бесплатной работающей VM. Не тарифицируется
только выключенная VM; диск и публичный IP могут тарифицироваться отдельно.
Новый подходящий аккаунт может получить стартовый грант: для резидентов РФ — не
менее 4 000 ₽ на 60 дней. Карту необходимо привязать при создании первого
платёжного аккаунта. Условия зависят от типа и страны аккаунта.

Поэтому ниже «бесплатный вариант» означает пилот, оплаченный стартовым грантом,
а не обещание вечного тарифа 0 ₽.

Официальные источники:

- https://yandex.cloud/ru/docs/getting-started/usage-grant
- https://yandex.cloud/ru/docs/compute/pricing
- https://yandex.cloud/ru/docs/billing/operations/budgets

### Почему для пилота выбирается VM

- текущий код уже использует PostgreSQL и Docker Compose;
- scheduler и worker должны работать постоянно;
- не требуется переписывать транзакции и Alembic под другую БД;
- локальный и облачный контуры максимально одинаковы;
- rollback — запуск предыдущего image tag и восстановление `pg_dump`.

### YC00 — Платёжный аккаунт и защита от расходов

1. Создать первый платёжный аккаунт и сразу привязать карту, если аккаунт
   соответствует условиям гранта.
2. Создать отдельные cloud/folder `mdr-pilot`, чтобы расходы проекта были видны
   отдельно.
3. В Billing → Budgets создать уведомления по фактической стоимости и остатку
   гранта, например 25%, 50%, 80% и 95%.
4. Помнить: бюджет отправляет уведомление, но сам по себе не останавливает
   ресурсы.

**DoD:** виден грант и дата окончания; уведомления бюджета подтверждены; вне
`mdr-pilot` нет случайных ресурсов.

### YC01 — VM и сеть

Создать Ubuntu LTS VM для пилота:

- 2 vCPU с уровнем производительности 20%;
- 2 ГБ RAM для малой нагрузки; при OOM перейти на 4 ГБ;
- 20 ГБ сетевого диска;
- один публичный IPv4;
- security group: `22/tcp` только с IP администратора, `80/443` из интернета;
- Docker Engine и Compose plugin.

Не размещать production на прерываемой VM: внезапная остановка нарушит webhook,
напоминания и утреннюю сводку.

**DoD:** SSH доступен только с разрешённого IP; закрыты все лишние порты;
Docker запускает `hello-world`; время и timezone корректны.

### YC02 — HTTPS-адрес

Предпочтительно купить/использовать собственный домен и направить A-запись на
VM. Caddy автоматически выпустит TLS-сертификат. Cloud DNS может хранить зону,
но регистрация домена не входит в free tier.

Для короткого бесплатного пилота допустим технический HTTPS-поддомен, зависящий
от публичного IP, но его нельзя считать надёжным production-доменом.

**DoD:** `https://<domain>/api/health` возвращает 200; HTTP перенаправляется на
HTTPS; сертификат валиден с телефона.

### YC03 — Доставка application image

Собирать image локально или в CI, присваивать неизменяемый tag с commit SHA и
загружать в Yandex Container Registry. На VM выполнять только pull, миграцию и
запуск — это снижает потребление RAM и делает rollback повторяемым.

Хранение образов в Container Registry тарифицируется, поэтому оставлять один
активный и один rollback tag, старые неиспользуемые образы удалять по политике.

Официальный источник: https://yandex.cloud/ru/docs/container-registry/pricing

**DoD:** digest локального и скачанного image совпадает; vulnerability scan не
имеет critical finding; предыдущий tag доступен для rollback.

### YC04 — Данные, секреты и запуск

1. Создать `/opt/mdr/.env` с правами `600`; не помещать секреты в image или git.
2. Создать отдельные сильные `POSTGRES_PASSWORD`, `MAX_WEBHOOK_SECRET` и
   `INTERNAL_TOKEN`.
3. Запустить PostgreSQL, выполнить `alembic upgrade head`.
4. Импортировать проверенный Excel со справочниками.
5. Запустить API, worker, scheduler и Caddy.
6. Зарегистрировать MAX webhook на облачный HTTPS URL.
7. Создать первый зашифрованный `pg_dump` вне VM.

Lockbox безопаснее файла `.env`, но тарифицируется. Для пилота `.env` с правами
`600`, ограниченным SSH и зашифрованным backup допустим как осознанный компромисс.

**DoD:** контейнеры healthy; API без MAX initData возвращает 401; internal
endpoint без токена отклоняется; webhook зарегистрирован; backup восстанавливается
в отдельную test-БД.

### YC05 — Облачная приёмка

Повторить матрицу O08 уже через облачный URL. Дополнительно:

- остановить и запустить API — данные сохраняются;
- остановить worker, создать отчёт, запустить worker — карточка приходит один раз;
- проверить выполнение всех четырёх расписаний по Москве;
- проверить Billing через 24 часа;
- записать фактический расход гранта и прогноз до конца 60 дней.

**DoD:** один ответственный сдаёт отчёты по двум объектам с телефона; группа
получает карточки и утреннюю сводку; табель и Excel сходятся; rollback проверен.

## Постоянный free-tier: отдельный трек, не быстрый deploy

Технически небольшое приложение можно приблизить к 0 ₽ в месяц через:

- Yandex Serverless Containers: 1 000 000 вызовов, 10 ГБ×час RAM и
  5 vCPU×час обработки запросов в месяц без тарификации;
- YDB Serverless: 1 000 000 RU и 1 ГБ хранения в месяц;
- timer triggers вместо постоянно работающего scheduler;
- прямой публичный HTTPS URL контейнера без собственной VM;
- Object Storage для небольших backup/export файлов в пределах free tier.

Официальные источники:

- https://yandex.cloud/ru/docs/billing/concepts/serverless-free-tier
- https://yandex.cloud/ru/docs/serverless-containers/operations/invocation-link
- https://yandex.cloud/ru/docs/serverless-containers/operations/container-public
- https://yandex.cloud/en/docs/serverless-containers/concepts/trigger/timer

Но текущий проект нельзя просто перенести туда одним deploy:

1. `asyncpg` и PostgreSQL Alembic migrations нужно заменить/адаптировать под
   `ydb-sqlalchemy` и YQL.
2. PostgreSQL pgwire-совместимость YDB находится в разработке и не рекомендуется
   для production, поэтому подмена только строки подключения небезопасна.
3. Scheduler и worker нужно превратить в идемпотентные timer-trigger handlers.
4. Нужно заново доказать транзакционные инварианты outbox и обязательств.
5. Container Registry и Lockbox имеют тарифицируемые составляющие, поэтому
   абсолютный и вечный 0 ₽ гарантировать нельзя даже при малой нагрузке.

Этот трек начинать только после успешного VM-пилота и замера реальной нагрузки.
До этого оптимизация облачной цены дороже и рискованнее самого маленького VM.

## Порядок выполнения

`O00 → O01 → O02 → O03 → O04 → O05 → O06 → O07 → O08 → YC00 → YC01 → YC02 → YC03 → YC04 → YC05`.

Первый следующий шаг — только O00. Он создаёт воспроизводимый Docker quality
gate, на котором затем безопасно строятся модель объектов и облачный deploy.
