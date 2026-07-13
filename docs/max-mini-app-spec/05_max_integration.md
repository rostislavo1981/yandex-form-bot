# 05. Интеграция с MAX

> **Важно.** Точные названия эндпоинтов MAX Bot API и JS-объекта Mini App должны быть взяты из **актуальной официальной документации** MAX перед реализацией. Ниже описан контракт по аналогии с Telegram Bot API (MAX построен на схожей модели). Пункты, помеченные `[непроверено]`, — гипотезы, требующие подтверждения.

## 5.1. Получение токена бота

1. Открыть чат с `@BotFather` в MAX (или их эквивалент — уточнить).
2. Команда `/newbot` → задать имя и username.
3. Получить `MAX_BOT_TOKEN` вида `<bot_id>:<hex>`.
4. Сохранить в `.env` — **никогда** не коммитить.

## 5.2. Регистрация Mini App

1. В BotFather MAX (или админке): `/newapp` → выбрать бота.
2. Указать публичный HTTPS-URL Mini App: `https://<domain>/`.
3. Указать иконку 640×360 PNG.
4. Сохранить.

## 5.3. Bot API — минимальный набор

**Base URL:** `https://api.max.ru/bot<TOKEN>/` `[непроверено — уточнить хост]`

| Метод | Назначение |
|---|---|
| `getUpdates` | Long polling |
| `sendMessage` | Отправить текст + inline-клавиатуру |
| `answerCallbackQuery` | Ответить на нажатие callback-кнопки |
| `setMyCommands` | Зарегистрировать список `/`-команд |

### Пример `sendMessage` с кнопкой Mini App
```json
POST /bot<TOKEN>/sendMessage
{
  "chat_id": 12345,
  "text": "Открой форму отчёта:",
  "reply_markup": {
    "inline_keyboard": [[
      {
        "text": "📝 Отчёт",
        "web_app": {"url": "https://<domain>/"}
      }
    ]]
  }
}
```

`[непроверено]` — в MAX это может называться `mini_app` вместо `web_app`. Уточнить.

## 5.4. Long polling — цикл

```python
async def poll_loop():
    offset = 0
    while True:
        updates = await max_client.get_updates(offset=offset, timeout=25)
        for u in updates:
            offset = u["update_id"] + 1
            await handle_update(u)
```

Обработчик:
```python
async def handle_update(u):
    msg = u.get("message")
    if not msg:
        return
    text = msg.get("text", "")
    chat_id = msg["chat"]["id"]
    user = msg["from"]

    if text == "/start" or text == "/help":
        await reply_help(chat_id)
    elif text == "/report":
        await reply_open_form(chat_id)
    elif text == "/summary":
        await reply_open_summary(chat_id)
    else:
        await max_client.send_message(chat_id, "Команда не распознана. /help")
```

## 5.5. Mini App — данные авторизации

При открытии Mini App клиент MAX инжектит в глобал JS-объект строку initData:

```js
// [непроверено — реальное имя объекта уточнить]
const initData = window.MaxApp?.initData || window.Telegram?.WebApp?.initData || "";
```

Формат `initData` — query-string:
```
user_id=12345&auth_date=1720800000&hash=<hex>
```

Frontend прикрепляет её ко всем API-запросам:
```js
fetch("/api/bootstrap", {
  headers: {"X-Auth-InitData": initData}
});
```

## 5.6. HMAC-верификация на backend

Файл: `backend/app/webapp_auth.py`

```python
import hashlib
import hmac
import time
from urllib.parse import parse_qsl

MAX_AUTH_TTL_SEC = 24 * 3600


class InitDataError(Exception):
    pass


def verify_init_data(init_data: str, bot_token: str) -> dict[str, str]:
    """Verify MAX Mini App initData. Return dict of validated fields.

    Raises InitDataError on failure.

    NOTE: assumes Telegram-style HMAC. Confirm against MAX docs before prod.
    """
    if not init_data:
        raise InitDataError("empty initData")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise InitDataError("missing hash")

    data_check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hashlib.sha256(bot_token.encode()).digest()
    expected = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, received_hash):
        raise InitDataError("bad signature")

    auth_date = int(pairs.get("auth_date", "0"))
    if time.time() - auth_date > MAX_AUTH_TTL_SEC:
        raise InitDataError("initData expired")

    return pairs
```

Использование в FastAPI:
```python
from fastapi import Header, HTTPException, Depends

async def require_max_user(
    x_auth_init_data: str = Header(...),
    settings: Settings = Depends(get_settings),
) -> User:
    try:
        data = verify_init_data(x_auth_init_data, settings.max_bot_token)
    except InitDataError as e:
        raise HTTPException(401, f"Auth failed: {e}")
    max_user_id = data["user_id"]
    user = await user_repo.get_by_max_id(max_user_id)
    if not user:
        raise HTTPException(403, "Unknown user")
    return user
```

## 5.7. Локальный dev-режим (без реального MAX)

Когда `APP_ENV=dev` и `MAX_BOT_TOKEN` пустой/`dev-token`:
- Middleware пропускает запросы без `X-Auth-InitData`.
- Подставляется фиктивный пользователь с `max_user_id="dev-1"` (тот, что в seed).
- Bot-процесс не стартует (или пишет updates в лог).

Это позволяет разрабатывать форму, открывая её в браузере на `http://localhost:8080/`.

## 5.8. Что должен вернуть бот на команды

**`/start` и `/help`:**
```
Привет! Я собираю ежедневные отчёты по объектам.

Команды:
/report — открыть форму отчёта
/summary — сводная за период
/help — эта справка
```

**`/report`:** сообщение с кнопкой открытия Mini App (см. 5.3).

**`/summary`:** сообщение с кнопкой открытия Mini App на URL `/summary` (или тот же URL + query `?tab=summary`).

## 5.9. Регистрация команд (один раз при старте бота)

```python
await max_client.set_my_commands([
    {"command": "report", "description": "Открыть форму отчёта"},
    {"command": "summary", "description": "Сводная за период"},
    {"command": "help", "description": "Справка"},
])
```

## 5.10. Что делать, если MAX Bot API отличается

Если после чтения официальной документации выяснится, что MAX использует:
- другой формат подписи initData → переписать `webapp_auth.verify_init_data`;
- другой хост API → изменить константу `MAX_API_BASE` в `MaxClient`;
- Webhook вместо polling → добавить `POST /webhook/max` эндпоинт, отключить polling.

**Ядро приложения (модель, API отчётов, frontend) от этого не меняется.**
