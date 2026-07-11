# Architecture

## Поток данных (end-to-end)

### 1. Отчёт прораба

```
MAX chat  ──текст──▶  Bot polling
                       │
                       ▼
                backend.llm.parser.parse_report
                       │
              ┌────────┴────────┐
              ▼                 ▼
       YandexGPT (lite)    extract_json
              │                 │
              └──── JSON ───────┘
                       │
                       ▼
                backend.schemas.Report (pydantic v2)
                       │
                       ▼
                backend.forms.filler.fill_form
                       │
                       ▼
            Playwright.fill(selector, value)
                       │
                       ▼
                submit()  →  screenshot()
                       │
                       ▼
            Report.screenshot  ─┬─▶  data/submissions/
                                 │
                                 └─▶  Yandex Disk
                                       (JSON + PNG)
                       │
                       ▼
                SubmissionDAO.insert (SQLite)
                       │
                       ▼
                PipelineResult → MAX reply
```

### 2. Mini App (сводная)

```
/webapp button  ──▶  MaxClient.sendMessage(reply_markup=web_app)
                              │
                              ▼
                  User taps "📊 Открыть"
                              │
                              ▼
                  MAX WebView loads /miniapp/index.html
                              │
                              ▼
                  window.WebApp.initData  (HMAC-signed)
                              │
                              ▼
                  fetch(/api/summary?date_from=…&date_to=…)
                       headers: X-Auth-InitData: <initData>
                              │
                              ▼
                  backend.webapp_auth.verify_init_data
                       - SHA256(bot_token) → secret
                       - hmac.compare_digest(hash)
                       - replay check (auth_date < 24h)
                              │
                              ▼
                  backend.api.get_summary
                              │
                              ▼
                  SubmissionDAO.list_by_date
                              │
                              ▼
                  JSON: {date_from, date_to, count, submissions[]}
                              │
                              ▼
                  Mini App renders cards + stats
                              │
                              ▼
                  Click on card → modal with screenshot
```

## Компоненты

| Модуль | Назначение | Тесты |
|---|---|---|
| `backend/schemas.py` | Pydantic-модели Report, MachineItem, Personnel, Material | 12 |
| `backend/llm/` | YandexGPT client + parser (fix-retry) + system prompt | 9 |
| `backend/forms/` | PlaywrightFormClient (Protocol + Fake + Real) + filler | 16 |
| `backend/disk/` | YandexDiskClient (auto-refresh OAuth) + archive | 8 |
| `backend/db/` | SubmissionDAO (SQLite) | 6 |
| `backend/excel/` | build_summary (openpyxl) + safe_str/safe_float | 10 |
| `backend/pipeline.py` | run_pipeline (4 стадии, best-effort) | 4 |
| `backend/max/` | MaxClient (Telegram-style) + bot loop + commands | 7+5+3 |
| `backend/api.py` | FastAPI для Mini App | 14 |
| `backend/webapp_auth.py` | HMAC verify MAX initData | 5 |

**Итого: 152 теста, 25 модулей.**

## Граничные условия

### Parser tolerance
- Пустые `machine_type` отфильтрованы в `Report._strip_empties`
- LLM может вернуть markdown ```json``` → `extract_json` снимает fences
- LLM вернул невалидный JSON → retry с fix-prompt
- LLM вернул частичный JSON → retry с полным (или `ValidationError`)

### Filler tolerance
- `value_to_str(None) → ""` → `fill()` пропускает поле
- `value_to_str(50.0) → "50"` (без `.0` для целых)
- Если селектор не найден → `FormFillError`
- Если submit упал → `FormFillError` + `screenshot_during_error`

### Auth
- HMAC SHA256 secret = SHA256(bot_token) (Telegram convention)
- Replay-атака: auth_date > 24h → 401
- Missing hash / bad signature / expired → 401

### Безопасность
- Секреты только в `.env` (в .gitignore)
- `.env.example` — шаблон без реальных значений
- `MAX_BOT_TOKEN` — без него бот не стартует
- API защищён HMAC — открыть Mini App можно только из MAX

## Точки расширения

| Что | Где | Сложность |
|---|---|---|
| +130 полей формы | `backend/forms/fields.py:MVP_FIELDS` | 1 день |
| Реальные CSS-селекторы | `backend/forms/fields.py` (вместо placeholder-ов) | 0.5 дня |
| Inline-редактирование | `PATCH /api/submissions/{id}` + UI в miniapp | 2 дня |
| Webhook вместо polling | новый `backend/max/webhook.py` | 1 день |
| Multi-prorab (без default_foreman) | `Report.foreman` уже есть, нужен UI | 1 день |
| Дашборд (графики) | Chart.js в miniapp | 1 день |
| Telegram-мост | MAX API совместим, можно реверснуть | 2 дня |
