# 12. Трек A: Bot-first — план фаз

**Идея трека:** сначала бот-опросник, потом (по желанию) Mini App.

Читать вместе с [`11_two_tracks.md`](./11_two_tracks.md) и [`13_bot_conversation.md`](./13_bot_conversation.md) (подробности стейт-машины опросника).

Ветки git: `phase-A0-bootstrap`, `phase-A1-model`, `phase-A2-reports-api`, `phase-A3-bot-conversation`, `phase-A4-summary-export`.

---

## Phase A0 — Bootstrap (1 день)

**Совпадает с Phase 0 из `08_implementation_plan.md` §Phase 0.**

Отличие только одно: в `docker-compose.yml` пока **не добавляем** сервисы `frontend` и `gateway` — они не нужны на этом треке.

**DoD:** `curl localhost:8000/api/health` → `{"status":"ok"}`.

---

## Phase A1 — Модель данных и БД (1 день)

**Полностью совпадает с Phase 1** из `08_implementation_plan.md`.

Endpoint `GET /api/bootstrap` тут технически не нужен для бота (он читает справочники напрямую через `dict_repo`), но реализовать его всё равно **надо** — пригодится для Phase A3 (Mini App), для отладки и для тестов.

**DoD:** `/api/bootstrap` возвращает справочники; тесты зелёные.

---

## Phase A2 — API отчётов (2 дня)

**Полностью совпадает с Phase 2** из `08_implementation_plan.md`.

Важное отличие: dependency `require_max_user` **не активируется** на этом этапе — авторизация происходит на уровне бота (см. Phase A3), а не по HMAC initData. Backend доверяет боту, который дёргает `POST /api/reports` изнутри compose-сети.

Защита backend'а:
- CORS — только localhost в dev.
- В prod backend вообще **не выставлен наружу** — Caddy/nginx проксирует только `/api/health` (или backend слушает на internal network без публичного порта).
- Bot вызывает backend по внутреннему адресу `http://backend:8000`, без HMAC.

**DoD:** `curl -X POST http://localhost:8000/api/reports -d '{...}'` создаёт отчёт; тесты зелёные.

---

## Phase A3 — Bot + стейт-машина диалога (2 дня)

Ключевая фаза этого трека. **Здесь и появляется прод-функциональность.**

### Задачи

1. `backend/app/max/client.py` — `MaxClient` (httpx). Все методы — реальный REST MAX API (см. `05_max_integration.md`):
   - `get_updates(marker: int | None, timeout: int = 25) -> list[dict]` — `GET /updates` (dev режим).
   - `subscribe_webhook(url: str, update_types: list[str]) -> None` — `POST /subscriptions` (prod).
   - `send_message(chat_id: int | None, user_id: int | None, text: str, attachments: list[dict] | None = None, format: str | None = None) -> dict` — `POST /messages`.
   - `answer_callback(callback_id: str, notification: str | None = None) -> None` — `POST /answers`.
   - `upload_file(file_bytes: bytes, filename: str, file_type: str = "file") -> str` — `POST /uploads`, возвращает token.
   - `get_chat(chat_id: int) -> dict` — `GET /chats/{id}`.

   Помощник для клавиатур:
   ```python
   def inline_keyboard(rows: list[list[dict]]) -> dict:
       return {"type": "inline_keyboard", "payload": {"buttons": rows}}

   def btn_callback(text: str, payload: str) -> dict:
       return {"type": "callback", "text": text, "payload": payload}

   def btn_message(text: str, payload: str) -> dict:
       return {"type": "message", "text": text, "payload": payload}

   def btn_link(text: str, url: str) -> dict:
       return {"type": "link", "text": text, "url": url}

   def btn_open_app(text: str) -> dict:
       return {"type": "open_app", "text": text}
   ```

2. `backend/app/max/state.py` — хранилище состояния диалога:
   - Класс `ConversationStore` с in-memory dict `chat_id → ConversationState`.
   - `ConversationState`: dataclass с полями `step: str`, `answers: dict`, `expected_input: str | None`, `last_message_id: int | None`.
   - Опционально TTL (напр. 30 мин без активности → сброс).

3. `backend/app/max/dialog.py` — стейт-машина отчёта:
   - Функция `next_step(state, update) -> tuple[NewState, ReplyPlan]`.
   - Шаги описаны в [`13_bot_conversation.md`](./13_bot_conversation.md).

4. `backend/app/max/handlers.py`:
   - `/start`, `/help` — приветствие и справка.
   - `/report` — запуск нового диалога.
   - `/cancel` — сброс текущего диалога.
   - `/summary`, `/export` — на Phase A4.
   - callback_query — обработка нажатий inline-кнопок.
   - text-сообщение — если ждём число, парсим; иначе — подсказка.

5. `backend/app/max/poller.py` — long polling с `marker` cursor. Формат:
   ```python
   async def run(client: MaxClient, dispatch):
       marker: int | None = None
       while True:
           batch = await client.get_updates(marker=marker, timeout=25)
           for upd in batch.get("updates", []):
               await dispatch(upd)
           marker = batch.get("marker", marker)
   ```

6. `backend/app/max/webhook.py` — endpoint `POST /webhook/max` для прод-режима (см. ADR-009).
   Проверяет заголовок `Authorization` совпадает с `MAX_BOT_TOKEN`, вызывает тот же `dispatch(upd)`.

7. `backend/app/bot.py`:
   ```python
   async def main():
       settings = get_settings()
       client = MaxClient(settings.max_bot_token, settings.max_api_base)
       store = ConversationStore()
       dispatch = make_dispatcher(client, store, backend_url=settings.backend_url)

       # Регистрация команд бота — способ уточнить в кабинете разработчика MAX.
       # [непроверено] есть ли API-метод; возможно, команды регистрируются один раз при создании бота.

       if settings.app_env == "prod":
           await client.subscribe_webhook(
               url=f"{settings.public_url}/webhook/max",
               update_types=["message_created", "message_callback"],
           )
           # Webhook принимает FastAPI-приложение, bot-процесс просто ждёт shutdown.
           await asyncio.Event().wait()
       else:
           await poller.run(client, dispatch)
   ```

7. В `docker-compose.yml` — сервис `bot`:
   ```yaml
   bot:
     build: ./backend
     command: python -m app.bot
     env_file: .env
     environment:
       BACKEND_URL: http://backend:8000
     depends_on:
       backend: {condition: service_started}
   ```

### Тесты

- `test_dialog.py` — стейт-машина без реального MAX: подаём `update`, проверяем `NewState` и `ReplyPlan`.
- `test_max_client.py` — httpx-моки для `send_message` / `get_updates`.
- Интеграционный: полный сценарий «диалог до конца» вызывает `POST /api/reports`, запись появляется в БД.

### DoD

- Получен токен от BotFather MAX.
- В чате `/report` запускает опросник.
- Диалог по сценарию из [`13_bot_conversation.md`](./13_bot_conversation.md) до конца.
- Подтверждение сохраняет отчёт в БД (проверить SQL'ом).
- `/cancel` работает на любом шаге.
- Тесты зелёные.

---

## Phase A4 — `/summary` и `/export` (1 день)

### Задачи

1. `backend/app/services/summary_service.py` — уже сделан в общем API, но добавить формирование текстовой карточки для чата.

2. `backend/app/max/handlers.py`:
   - `/summary` — принимает опционально дату (`/summary 2026-07-13`) или чипы кнопками (Сегодня/Вчера/7 дней/30 дней).
   - `/export` — запрос диапазона + отправка XLSX-файла в чат.

3. Отправка Excel в чат — двухшаговый (см. `05_max_integration.md` §5.10):
   ```python
   token = await client.upload_file(xlsx_bytes, "reports_2026-07-13.xlsx", file_type="file")
   await client.send_message(
       chat_id=chat_id,
       text="📥 Отчёты за 13.07",
       attachments=[{"type": "file", "payload": {"token": token}}],
   )
   ```

### Формат ответа `/summary`

```
📊 Сводная за 13.07.2026

Отчётов: 5
Всего людей: 34
Часов техники: 42
Грунт: 120.5 м³

По объектам:
• БОГ-КЛ-04 — 3 отчёта, 80.5 м³
• РСТИ-БКТП-3 — 2 отчёта, 40 м³

📥 /export 2026-07-13 — скачать Excel
```

### Формат `/export`

Бот сразу присылает файл с корректным именем `reports_2026-07-13.xlsx`. Если много данных — сначала «Формирую…», потом файл.

### DoD

- В чате команда `/summary` присылает карточку.
- Команда `/export` присылает файл, он открывается в LibreOffice/Excel.
- Тесты зелёные.

---

## Phase A5 — Прод-деплой (1 день)

По ADR-009 на проде обязателен webhook (long polling ограничен по rate). Значит нужен HTTPS-эндпоинт `/webhook/max` — но всего один, без frontend'а.

1. `docker-compose.prod.yml` — сервисы `db`, `backend`, `bot`, `caddy`.
2. `Caddyfile`:
   ```
   <domain> {
     encode gzip
     reverse_proxy /webhook/max backend:8000
     reverse_proxy /api/health backend:8000
     # /api/* — только внутри compose-сети (не выставлять наружу),
     # если нужен внешний доступ для интеграций — раскомментировать:
     # reverse_proxy /api/* backend:8000
   }
   ```
3. `deploy/install.sh` — apt install docker, git clone, cp .env, `docker compose -f docker-compose.prod.yml up -d`.
4. После старта — бот сам вызовет `POST /subscriptions`, MAX начнёт слать updates.
5. Реальный тест: `/report` с телефона.

### DoD

- На VPS работает `docker compose ps` → все контейнеры up.
- Бот отвечает в MAX с телефона.
- Reset БД через `docker compose down -v` + `up -d` — сохранились seed'ы.

---

## Phase A6 (опционально) — Mini App поверх готового ядра

Если позже понадобится Mini App, делается всё то же самое, что описано в `08_implementation_plan.md` §Phase 3, 4, 5 (Frontend + HMAC).

**Ничего в модели и API менять не нужно** — Mini App просто становится вторым клиентом того же backend'а.

Оценка: 7–8 дней (те же цифры, что и Track B, только сдвинуты во времени).

---

## Итого по трекам

| Трек | До прод-релиза | Полный MVP |
|---|---|---|
| **A (Bot-first)** | ~7 дней (Phase 0+1+2+A3+A4) | те же ~7 дней |
| **B (MiniApp-first)** | ~12 дней (Phase 0+1+2+3+4+5+6) | ~12 дней |
| **A + опциональная A6** | 7 дней бот, +7 дней Mini App | ~14 дней |
| **B + опциональный бот-опросник** | 12 дней Mini App, +3 дня бот | ~15 дней |

Трек A даёт **работающий продукт быстрее**, при этом **не блокирует** будущее расширение до Mini App.
