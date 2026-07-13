# 05. Интеграция с MAX

> **Источник:** [dev.max.ru/docs](https://dev.max.ru/docs) и [dev.max.ru/docs-api](https://dev.max.ru/docs-api). Все методы и параметры сверены с официальной документацией (июль 2026). Пункты, помеченные `[непроверено]`, требуют дополнительной сверки перед реализацией — обычно это детали, не найденные в кратких reference-страницах.

## 5.1. Получение токена бота

1. Открыть кабинет разработчика MAX и создать бота (через `@MasterBot` или веб-кабинет — уточнить актуальный способ).
2. Получить токен вида длинной hex-строки.
3. Сохранить в `.env` как `MAX_BOT_TOKEN` — **никогда** не коммитить.

## 5.2. Базовый URL и авторизация

**Base URL:** `https://platform-api2.max.ru`

**Авторизация:** заголовок HTTP-запроса.
```
Authorization: <MAX_BOT_TOKEN>
```
Передача токена через query-параметры **больше не поддерживается**.

Все ответы — JSON. Content-Type запросов — `application/json`.

## 5.3. Регистрация Mini App

1. В кабинете разработчика создать mini app, привязать к боту.
2. Указать публичный HTTPS-URL: `https://<domain>/`.
3. Указать иконку.
4. Сохранить.

Mini App открывается кнопкой типа `open_app` или через deep-link (см. 5.11).

## 5.4. Bot API — используемые методы

| Метод | Endpoint | Назначение |
|---|---|---|
| Отправить сообщение | `POST /messages` | Текст + inline-кнопки |
| Получить updates (dev) | `GET /updates` | Long polling |
| Подписаться на webhook (prod) | `POST /subscriptions` | Регистрация callback URL |
| Ответ на callback-кнопку | `POST /answers` | Подтверждение нажатия |
| Загрузить файл | `POST /uploads` | Возвращает `token` для attachment |
| Работа с чатом | `GET/PATCH /chats/{chatId}` | Инфо о чате, изменение настроек |
| Действия над чатом | `POST /chats/{chatId}/actions` | Закрепление и т.п. `[непроверено]` |
| Участники | `GET/POST/DELETE /chats/{chatId}/members` | |

`[непроверено]` — точный endpoint для «зарегистрировать /-команды в меню» (аналог Telegram `setMyCommands`) в кратком reference не найден. Возможно, задаётся при создании бота в кабинете, а не через API. Проверить перед Phase A3.

## 5.5. Отправка сообщения

```
POST /messages
Authorization: <TOKEN>
Content-Type: application/json

{
  "chat_id": 12345,
  "text": "Открой форму отчёта:",
  "format": "markdown",
  "attachments": [
    {
      "type": "inline_keyboard",
      "payload": {
        "buttons": [
          [{"type": "open_app", "text": "📝 Отчёт"}]
        ]
      }
    }
  ]
}
```

Альтернатива: вместо `chat_id` можно указать `user_id` для отправки в личный чат.

Формат текста: `format: "markdown"` или `"html"`.

## 5.6. Типы inline-кнопок

Документация MAX поддерживает 7 типов кнопок:

| Тип | Что делает | Как использовать в проекте |
|---|---|---|
| `callback` | Присылает боту событие `message_callback` с `payload` | Выбор объекта, этапа, техники в диалоге |
| `link` | Открывает URL | Ссылки на документы, deep-link |
| `open_app` | Открывает mini app | Кнопка «Открыть форму» |
| `message` | Отправляет заранее заготовленное сообщение от имени пользователя | Пульт в группе: `[📝 Сдать отчёт]` → шлёт `/report` |
| `request_contact` | Просит поделиться контактом | Онбординг (можно не использовать) |
| `request_geo_location` | Просит геолокацию | Не нужен в MVP |
| `clipboard` | Копирует текст в буфер | Не нужен в MVP |

**Лимиты клавиатуры:**
- До 210 кнопок всего.
- До 30 рядов.
- До 7 обычных кнопок в ряду; до 3 для `link` / `request_contact`.

**Пример callback-кнопки:**
```json
{
  "type": "callback",
  "text": "БОГ-КЛ-04",
  "payload": "obj:10"
}
```

**Пример message-кнопки (для пульта в группе):**
```json
{
  "type": "message",
  "text": "📝 Сдать отчёт",
  "payload": "/report"
}
```

## 5.7. Получение обновлений

### Long polling (dev)
```
GET /updates?marker=<n>&timeout=25&limit=100
Authorization: <TOKEN>
```
Возвращает список updates и следующий `marker` для очередного вызова.

Документация MAX **явно предупреждает**: long polling ограничен по rate, для прода не рекомендуется.

### Webhook (prod)
```
POST /subscriptions
Authorization: <TOKEN>
Content-Type: application/json

{"url": "https://<domain>/webhook/max", "update_types": ["message_created", "message_callback"]}
```
После регистрации MAX POST'ит updates на указанный URL.

Полный набор `update_types` — см. документацию `/subscriptions`. Для MVP достаточно:
- `message_created` — новое сообщение (текст, команда).
- `message_callback` — нажатие callback-кнопки.

`[непроверено]` — полный список update_types и точная схема каждого. Уточнить перед реализацией handler'ов.

## 5.8. Формат update

Каждый update содержит тип и полезную нагрузку. По документации точная схема для `message_callback` не приведена в кратком reference; ниже — **гипотетическая структура** для проектирования handler'ов (`[непроверено]`, скорректировать при получении первого реального update):

```json
{
  "update_type": "message_created",
  "message": {
    "message_id": 100500,
    "chat": {"chat_id": 12345, "type": "dialog"},
    "sender": {"user_id": 42, "name": "Казнадеев И."},
    "text": "/report",
    "timestamp": 1720800000
  }
}
```

```json
{
  "update_type": "message_callback",
  "callback": {
    "callback_id": "abc123",
    "message_id": 100500,
    "chat": {"chat_id": 12345},
    "user": {"user_id": 42, "name": "Казнадеев И."},
    "payload": "obj:10"
  }
}
```

**Первое, что делает бот в проде:** логирует raw JSON первых 20 updates и правит схемы, если они отличаются.

## 5.9. Ответ на callback

После обработки нажатия callback-кнопки бот должен подтвердить:
```
POST /answers
Authorization: <TOKEN>
Content-Type: application/json

{
  "callback_id": "abc123",
  "notification": "Выбрано: БОГ-КЛ-04"
}
```
`notification` — короткий текст, MAX показывает как эфемерное уведомление у нажавшего.

`[непроверено]` — таймаут ответа (в Telegram ~30 сек). Если не ответить вовремя, кнопка «зависнет» с индикатором ожидания.

## 5.10. Отправка файла (Excel)

Двухшаговый процесс:

**Шаг 1.** Получить upload-token:
```
POST /uploads?type=file
Authorization: <TOKEN>
Content-Type: multipart/form-data

<файл>
```
Ответ: `{"token": "..."}`.

**Шаг 2.** Прикрепить к сообщению:
```
POST /messages
{
  "chat_id": 12345,
  "text": "📥 Отчёты за 13.07",
  "attachments": [{"type": "file", "payload": {"token": "..."}}]
}
```

Лимиты MAX: файлы до 4 GB. XLSX выгрузка укладывается с большим запасом.

## 5.11. Mini App — открытие и авторизация

### Как открывается

**Через кнопку `open_app`:**
```json
{"type": "open_app", "text": "📝 Форма"}
```

**Через deep-link (можно в любом сообщении, включая внешние):**
```
https://max.ru/<bot_username>?startapp=<payload>
```
При переходе:
1. MAX открывает чат с ботом (создаёт, если ещё нет).
2. Запускает mini app.
3. Строка `<payload>` попадает в webview как `WebApp.initDataUnsafe.start_param`.

Это ключевой механизм для **пульта в группе**: кнопка `link` с URL deep-link → прораб оказывается в личке с открытой формой, `start_param="report"` → форма сразу открывается на нужном экране.

### Что доступно в webview

Инжектится глобальный объект `window.WebApp`:

```js
window.WebApp.initData          // строка initData для верификации (см. 5.12)
window.WebApp.initDataUnsafe    // { user, chat, start_param, auth_date, hash, ... } — только для UI, НЕ для решений о правах
window.WebApp.initDataUnsafe.user       // { user_id, name, ... }
window.WebApp.initDataUnsafe.start_param // строка payload из deep-link или open_app
```

Дополнительно доступны (по документации MAX Bridge):
- Управление экраном.
- Скачивание файлов (требует HTTPS).
- Сканирование QR.
- Биометрия.
- NFC (Android).
- Device storage (шифрованный и обычный).

`[непроверено]` — метод программного закрытия mini app (в Telegram `WebApp.close()`). Уточнить в полной документации MAX Bridge.

### HTTPS обязателен для mini app и для скачивания файлов.

## 5.12. Верификация initData на backend

**Формула HMAC — отличается от Telegram!**

По документации MAX:
```
hash = HMAC_SHA256(authDate + phone + userId, botToken)
```

- Ключ HMAC — сам `botToken` (без SHA256-обёртки, как в Telegram).
- Data-check-string — конкатенация **только трёх** полей: `authDate`, `phone`, `userId` (не отсортированный список всех пар).

**Реализация** — файл `backend/app/webapp_auth.py`:

```python
import hashlib
import hmac
import time
from urllib.parse import parse_qsl

MAX_AUTH_TTL_SEC = 24 * 3600


class InitDataError(Exception):
    pass


def verify_init_data(init_data: str, bot_token: str) -> dict[str, str]:
    """Verify MAX Mini App initData.

    Формула MAX:
        hash = HMAC_SHA256(auth_date + phone + user_id, bot_token)

    Возвращает словарь параметров при успехе, кидает InitDataError при ошибке.
    """
    if not init_data:
        raise InitDataError("empty initData")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise InitDataError("missing hash")

    auth_date = pairs.get("auth_date", "")
    phone = pairs.get("phone", "")
    user_id = pairs.get("user_id", "")

    data_check = f"{auth_date}{phone}{user_id}"
    expected = hmac.new(
        bot_token.encode(),
        data_check.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, received_hash):
        raise InitDataError("bad signature")

    if not auth_date or time.time() - int(auth_date) > MAX_AUTH_TTL_SEC:
        raise InitDataError("initData expired")

    return pairs
```

`[непроверено]` — точное имя полей в initData (`auth_date` vs `authDate`, `user_id` vs `userId`) и наличие `phone` для пользователей, не поделившихся номером. Первый шаг реализации Phase A3/B3 — прологировать реальный initData от одного тестового пользователя, проверить имена полей.

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
    max_user_id = data.get("user_id")
    user = await user_repo.get_by_max_id(max_user_id)
    if not user:
        raise HTTPException(403, "Unknown user")
    return user
```

## 5.13. Работа в группах

### Типы чатов
Из документации: чат имеет `type`. Значения (по аналогии с dev.max.ru — `[непроверено]`, уточнить):
- `dialog` — приватный чат с ботом.
- `chat` или `group` — групповой чат.
- `channel` — канал.

### Обработка `chat.type`

```python
async def handle_message(update):
    chat = update["message"]["chat"]
    if chat["type"] == "dialog":
        await handle_private_message(update)
    else:
        await handle_group_message(update)
```

В группе:
- `/report` → бот отвечает «продолжим в личке» + кнопка `link` с deep-link `https://max.ru/<bot>?startapp=report`.
- `/summary`, `/export` → работают прямо в группе.
- `/register_here` (для manager/admin) → регистрирует чат как канал уведомлений.
- Кнопки типа `message` из закреплённого пульта → отправляют команду от имени нажавшего.

### Пульт в группе (закреплённое сообщение)

```
Пульт «Ежедневный отчёт»

Прораб — сдать сегодняшний отчёт:
[ 📝 Сдать отчёт ]

Руководителю:
[ Сегодня ] [ 7 дней ] [ 30 дней ]
[ 📥 Excel сегодня ] [ 📥 Excel 7 дней ]
```

Кнопки:
- «📝 Сдать отчёт» — тип `link` с URL `https://max.ru/<bot>?startapp=report` (открывает личку → mini app / диалог с готовым payload).
- «Сегодня»/«7 дней» — тип `message` с payload `/summary` / `/summary 7d` (отправляет команду в чат, бот отвечает сводкой в тот же чат).
- «📥 Excel» — тип `message` с payload `/export` / `/export 7d`.

`[непроверено]` — нужны ли боту админ-права в группе для закрепления сообщения. Метод закрепления — вероятно `POST /chats/{id}/actions` с action `pin_message` (уточнить).

## 5.14. Локальный dev-режим (без реального MAX)

Когда `APP_ENV=dev`:
- Backend пропускает запросы без `X-Auth-InitData` и подставляет фиктивного пользователя (`max_user_id="dev-1"`).
- Bot-процесс можно вообще не запускать; форму открывать в браузере на `http://localhost:8080/`.

## 5.15. Регистрация /-команд бота

`[непроверено]` — точный endpoint. Гипотезы:
1. В кабинете разработчика при создании бота.
2. Через `PATCH /me` или аналог.

Если API-метода нет, регистрировать вручную при создании бота — это одноразовое действие, не блокирует MVP.

Наш минимальный набор:
- `/report` — сдать отчёт
- `/summary` — сводная за период
- `/export` — Excel-выгрузка
- `/cancel` — отменить текущий диалог
- `/help` — справка

## 5.16. Что делать, если реальный API окажется отличным

Все взаимодействия с MAX инкапсулированы в двух файлах:
- `backend/app/max/client.py` — вызовы Bot API.
- `backend/app/webapp_auth.py` — верификация initData.

Остальной код (модель, API отчётов, стейт-машина диалога, frontend) от MAX не зависит и **не меняется** при любых изменениях протокола.

## 5.17. Список открытых вопросов

Перед началом Phase A3/B3 обязательно проверить (см. `[непроверено]` выше):
1. Точная схема update `message_callback` (поля payload/user/chat/message_id).
2. Таймаут ответа на callback через `POST /answers`.
3. Endpoint для регистрации `/`-команд бота.
4. Точные имена полей в initData (`auth_date` vs `authDate` и т.д.).
5. Значение `chat.type` для групповых чатов.
6. Нужны ли админ-права боту для закрепления сообщений.
7. Метод программного закрытия mini app.
8. Полный список `update_types` для `POST /subscriptions`.

**Как проверять:** создать тестового бота, отправить одному пользователю сообщение с callback-кнопкой, залогировать реальные updates. По ним — правки в handlers и схемы.
