# REST API для Mini App

> Контракт V1. Новый MVP-контракт: [`max-mini-app-spec/04_api_contract.md`](max-mini-app-spec/04_api_contract.md).

Базовый URL: `https://bot.example.com/api`

Все endpoints (кроме `/healthz`) требуют заголовок `X-Auth-InitData` с подписанной MAX-строкой.

## Аутентификация

MAX WebApp SDK выставляет `window.WebApp.initData` — URL-encoded строку с `hash`. Backend проверяет HMAC SHA256 (secret = SHA256(bot_token)).

```http
GET /api/summary?date_from=2026-07-10&date_to=2026-07-10
X-Auth-InitData: user=%7B%22id%22%3A42%7D&auth_date=1720700000&query_id=abc&hash=...
```

При невалидной/просроченной подписи → 401.

## Endpoints

### `GET /api/healthz`
Публичный health-check.

**Ответ:** `200 {"ok": true}`

### `GET /api/summary`
Список отчётов за период.

**Query params:**
- `date_from` (опц., ISO YYYY-MM-DD, default: 7 дней назад)
- `date_to` (опц., ISO YYYY-MM-DD, default: сегодня)
- `foreman` (опц., фильтр по прорабу, case-insensitive)

**Ответ 200:**
```json
{
  "date_from": "2026-07-04",
  "date_to": "2026-07-11",
  "count": 3,
  "submissions": [
    {
      "id": 1,
      "date": "2026-07-10",
      "object_name": "РП-7 Каменка",
      "foreman": "Степанов",
      "machines": [
        {"machine_type": "Экскаватор JCB 3CX", "unit": "час", "quantity": 8}
      ],
      "personnel": {"itr": 1, "opr_staff": 4, "opr_external": 0},
      "personnel_total": 5,
      "waste_volume": 15,
      "comment": null,
      "final_comment": null,
      "weather": "ясно",
      "screenshot_path": "/data/submissions/2026-07-10_Степанов_...png",
      "screenshot_url": "/api/screenshot/1",
      "disk_json_url": "https://yadi.sk/d/...",
      "disk_png_url": "https://yadi.sk/d/...",
      "filled_at": "2026-07-10T18:32:11",
      "confirmed": true
    }
  ]
}
```

### `GET /api/submissions/{sub_id}`
Один отчёт.

**Ответ 200:** тот же `submissions[i]`
**Ответ 404:** если не найден

### `GET /api/screenshot/{sub_id}`
Файл PNG (скриншот заполненной формы).

**Ответ 200:** `image/png`
**Ответ 404:** если нет `screenshot_path` или файл удалён

### `GET /api/summary.xlsx`
Excel-сводная за день.

**Query params:**
- `date` (опц., ISO YYYY-MM-DD, default: вчера)

**Ответ 200:** `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, имя `summary_<date>.xlsx`
**Ответ 404:** если нет отчётов за день

## Коды ошибок

| Код | Когда |
|---|---|
| 400 | Невалидный ISO date |
| 401 | Нет `X-Auth-InitData` / битая подпись / истёк |
| 404 | Submission / screenshot / xlsx не найден |
| 500 | `MAX_BOT_TOKEN` не настроен |

## CORS

CORS не выставляется явно — Mini App идёт с тем же origin (через nginx/Caddy reverse-proxy). Если кросс-домен нужен — добавить `CORSMiddleware` в `backend/api.py`.

## Примеры (curl)

```bash
# Сначала получить initData из браузера в MAX WebView
INIT=$(echo 'window.WebApp.initData' | node)

# Сводная
curl -H "X-Auth-InitData: $INIT" \
  "https://bot.example.com/api/summary?date_from=2026-07-10&date_to=2026-07-10"

# Excel
curl -H "X-Auth-InitData: $INIT" \
  -o summary.xlsx \
  "https://bot.example.com/api/summary.xlsx?date=2026-07-10"
```
