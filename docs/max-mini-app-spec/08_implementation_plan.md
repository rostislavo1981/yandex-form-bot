# 08. Пошаговый план реализации

Все фазы = отдельные ветки + PR + прогон тестов. Каждая фаза заканчивается **проверяемым критерием готовности** (Definition of Done). Слабой модели: **не переходить к следующей фазе, пока текущий DoD не выполнен**.

## Общие правила

- Работать в ветке `phase-N-<slug>`, мержить в `main` через PR.
- В каждом коммите — один осмысленный шаг.
- Перед PR: `make lint && make test` — обе команды зелёные.
- Не менять файлы за пределами описанной фазы, если явно не сказано.

---

## Phase 0 — Bootstrap (день 1)

**Цель:** пустой репозиторий превращается в скелет, `make up` поднимает БД и пустой backend.

**Задачи:**
1. `git init`, `README.md` (копия `01_overview.md` кратко), `.gitignore`, `.dockerignore`, `LICENSE` (MIT).
2. Создать структуру папок из `07_project_structure.md` (пустые файлы с `# TODO`).
3. `docker-compose.yml`:
   - `db`: postgres:16-alpine, healthcheck.
   - `backend`: build из `./backend`, uvicorn `app.main:app --reload`, зависит от `db`.
4. `backend/requirements.txt`:
   ```
   fastapi==0.115.*
   uvicorn[standard]==0.32.*
   sqlalchemy==2.0.*
   asyncpg==0.29.*
   pydantic==2.9.*
   pydantic-settings==2.6.*
   httpx==0.27.*
   openpyxl==3.1.*
   pytest==8.*
   pytest-asyncio==0.24.*
   ruff==0.7.*
   ```
5. `backend/Dockerfile` — python:3.12-slim + pip install.
6. `backend/app/main.py` — минимальный `FastAPI()` с `/api/health` → `{"status":"ok"}`.
7. `backend/app/config.py` — `Settings` (см. 07).
8. `.env.example` создать, `.env` в `.gitignore`.
9. `Makefile`.

**DoD:**
- `make up` работает, `curl localhost:8000/api/health` → `{"status":"ok"}`.
- `docker compose logs backend` без ошибок.
- Тестов ещё нет — это нормально.

---

## Phase 1 — Модель данных и БД (день 2)

**Цель:** таблицы созданы, справочники заполнены, `/api/bootstrap` отдаёт данные.

**Задачи:**
1. `backend/app/database.py` — async engine, sessionmaker, `Base`, `get_db()`.
2. `backend/app/models.py` — все таблицы из `03_data_model.md`.
3. `backend/app/seed.py` — данные из `03_data_model.md` §Seed.
4. `main.py` `lifespan`:
   ```python
   async with engine.begin() as conn:
       await conn.run_sync(Base.metadata.create_all)
   async with SessionLocal() as db:
       await seed_if_empty(db)
   ```
5. `backend/app/schemas.py` — Pydantic-схемы для bootstrap (см. `04_api_contract.md`).
6. `backend/app/repos/dict_repo.py` — `get_all_dictionaries()`.
7. `backend/app/api/bootstrap.py` — `GET /api/bootstrap` (без auth пока).
8. Подключить router в `main.py`.
9. Первый тест: `tests/test_bootstrap.py` — вызывает `/api/bootstrap`, проверяет структуру.

**DoD:**
- `curl localhost:8000/api/bootstrap` возвращает JSON со всеми справочниками.
- `pytest tests/test_bootstrap.py` — зелёный.
- В БД появились строки из seed (проверить `docker compose exec db psql -U mvp -d mvp -c '\dt'`).

---

## Phase 2 — Создание и чтение отчётов (день 3–4)

**Цель:** можно POST'ить отчёты и GET'ать их.

**Задачи:**
1. `backend/app/schemas.py` — добавить `DailyReportIn`, `EquipmentRowIn`, `WorkRowIn`, `DailyReportOut`, `DailyReportListItem`.
2. `backend/app/services/report_service.py`:
   - `async def create_report(db, payload, user)` — валидирует инварианты, INSERT'ит шапку и строки, возвращает `DailyReport`.
   - Все проверки из `03_data_model.md` §Инварианты.
3. `backend/app/repos/report_repo.py`:
   - `list_reports(filters, limit, offset)`
   - `get_report(id)` с загрузкой связей (`selectinload`).
4. `backend/app/api/reports.py`:
   - `POST /api/reports` (пока без auth) → возвращает `{"id":.., "status":..}`.
   - `GET /api/reports?date_from&date_to&object_id&responsible_user_id&mine&limit&offset`.
   - `GET /api/reports/{id}`.
5. Тесты:
   - `test_reports_create.py`: успех, отсутствие подрядчика для contractor-объекта, чужой этап, пустое содержимое.
   - `test_reports_list.py`: фильтр по датам.

**DoD:**
- `pytest -k reports` — зелёный.
- Ручной сценарий из `01_overview.md` §Happy Path (без бота) проходит через curl.
- В БД реально создаются строки в `daily_reports`, `report_equipment`, `report_works`.

---

## Phase 3 — Frontend MVP (день 5–7)

**Цель:** форма в браузере, отправляет реальный POST, показывает успех.

**Задачи:**
1. `frontend/package.json`: React 18, react-dom, TypeScript, Vite.
2. `frontend/Dockerfile` (multi-stage: node build → nginx static).
3. Добавить в compose сервис `frontend` и `gateway` (nginx на 8080).
4. `nginx.conf` — dev-версия (прокси на `frontend:5173` и `backend:8000/api/`).
5. `src/api.ts` — типы + `ApiClient` с методами `bootstrap()`, `createReport()`, `listReports()`, `getSummary()`.
6. `src/auth.ts`:
   ```ts
   export function getInitData(): string {
     // @ts-ignore - MAX injects MaxApp; fallback for dev
     return window.MaxApp?.initData || "dev-init";
   }
   ```
7. `src/contexts/BootstrapContext.tsx` — fetch, кэш, provider.
8. `src/pages/ReportForm.tsx` — экран из `06_frontend_spec.md` §Экран 1.
9. `src/pages/Summary.tsx` — заглушка «в разработке» (реализуется в Phase 4).
10. `src/App.tsx` — роутинг (или таб-переключение).
11. `src/styles/main.css` — минимальный мобильный лейаут.

**DoD:**
- `docker compose up` → открываем `http://localhost:8080/`, форма рендерится.
- Тестовый сценарий из `01_overview.md`: выбрать объект БОГ-КЛ-04, этап, добавить технику, отправить → «✅ Отчёт №N».
- Второй сценарий: подрядный объект РСТИ-БКТП-3 → показывается поле подрядчика, скрыт блок персонала.
- Запись реально появилась в БД.

---

## Phase 4 — Сводная и Excel (день 8)

**Цель:** экран сводной работает, скачивание xlsx работает.

**Задачи:**
1. `backend/app/services/summary_service.py` — агрегаты SQL (`SUM`, `COUNT`, `GROUP BY object_id`).
2. `backend/app/api/summary.py` — `GET /api/summary?date_from&date_to`.
3. `backend/app/services/excel_service.py` — построение workbook: 3 листа как в `04_api_contract.md`.
4. `backend/app/api/export.py` — StreamingResponse.
5. `frontend/src/pages/Summary.tsx` — полная реализация из `06_frontend_spec.md` §Экран 2.
6. Тесты: `test_summary.py`, `test_export_xlsx.py` (проверить, что файл открывается openpyxl и в нём 3 листа).

**DoD:**
- Экран `/summary` показывает карточки и список.
- Кнопка «Excel» скачивает файл, он открывается в LibreOffice/Excel, содержит корректные данные.
- Тесты зелёные.

---

## Phase 5 — Bot MAX + HMAC (день 9–11)

**Цель:** бот в MAX открывает Mini App; авторизация работает.

**Задачи:**
1. `backend/app/webapp_auth.py` — `verify_init_data` (см. `05_max_integration.md` §5.6).
2. `backend/app/deps.py` — `require_max_user` dependency.
3. Подключить dependency ко всем `/api/*` кроме `/health`.
4. **Dev-режим:** если `settings.app_env == "dev"` и `X-Auth-InitData` отсутствует — подставлять фикс-юзера. Реализовать через отдельный dependency, выбираемый в `deps.py` по env.
5. `backend/app/max/client.py` — `MaxClient` (см. `05` §5.3).
6. `backend/app/max/handlers.py` — обработчики `/start`, `/report`, `/summary`, `/help`.
7. `backend/app/max/poller.py` — цикл `get_updates`.
8. `backend/app/bot.py`:
   ```python
   async def main():
       settings = get_settings()
       client = MaxClient(settings.max_bot_token, settings.max_api_base)
       await client.set_my_commands([...])
       await poller.run(client, handlers)

   if __name__ == "__main__":
       asyncio.run(main())
   ```
9. Добавить в compose сервис `bot`.
10. Тесты `test_webapp_auth.py` (валидная/невалидная/протухшая подпись) и `test_max_client.py` (mock httpx).
11. Frontend: обновить `auth.ts` — читать реальный `window.MaxApp?.initData`.

**DoD:**
- Получен токен от BotFather MAX.
- Бот отвечает на `/start` в MAX.
- Кнопка «Открыть форму» открывает Mini App, форма загружается, отчёт сохраняется.
- Запрос без `X-Auth-InitData` возвращает 401 (в prod-режиме).
- Тесты зелёные.

> Если API MAX окажется отличным от Telegram-схемы: заменить содержимое `webapp_auth.py` и `MaxClient` без изменения всего остального.

---

## Phase 6 — Прод-деплой (день 12)

**Цель:** приложение работает на VPS по HTTPS-домену.

**Задачи:**
1. `docker-compose.prod.yml` — те же сервисы + `caddy` вместо nginx.
2. `Caddyfile`:
   ```
   <domain> {
     encode gzip
     handle /api/* {
       reverse_proxy backend:8000
     }
     handle {
       root * /srv/frontend/dist
       try_files {path} /index.html
       file_server
     }
   }
   ```
3. `deploy/install.sh` — скрипт первого развёртывания на Ubuntu (apt install docker, git clone, cp .env, `docker compose up -d`).
4. Регистрация Mini App в BotFather MAX с prod-URL.
5. Smoke-тест с реального телефона: `/report` → форма → отправка → запись в БД.

**DoD:**
- Сервер отвечает `https://<domain>/api/health` → 200.
- В браузере на телефоне открывается по HTTPS.
- MAX Mini App открывается по кнопке, работает end-to-end.

---

## Phase 7+ — на потом (не делать в MVP)

- Alembic-миграции.
- Админка справочников через UI.
- Черновики + PATCH-эндпоинт.
- Фото/файлы (загрузка на S3-совместимое хранилище).
- Webhook вместо polling.
- LLM-парсер (адаптация из проекта `yandex-form-bot`).
- Push-уведомления «не сдал отчёт до 20:00».
- Redis для кэша bootstrap.

---

## Оценка сроков

| Phase | Дни | Основная сложность |
|---|---|---|
| 0 | 1 | Инфра |
| 1 | 1 | Модель |
| 2 | 2 | Инварианты + тесты |
| 3 | 3 | Frontend + условная логика UI |
| 4 | 1 | Excel |
| 5 | 3 | HMAC MAX + прод-подключение |
| 6 | 1 | HTTPS + деплой |

**Итого: ~12 рабочих дней при одном разработчике.**
