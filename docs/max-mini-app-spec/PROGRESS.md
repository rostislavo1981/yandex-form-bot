# PROGRESS

Обновлено: 2026-07-14.

## Текущий статус

I13 завершена. MAX REST client + webhook handler + mock-тесты.

| Итерация | Статус | Результат |
|---|---|---|
| I00 | COMPLETED | Скелет `max_daily_report/`, health, PostgreSQL compose, тест |
| I01 | COMPLETED | База и миграции |
| I02 | COMPLETED | Seed справочников |
| I03 | COMPLETED | Поиск каталогов |
| I04 | COMPLETED | Excel validate |
| I05 | COMPLETED | Excel apply/export |
| I06 | COMPLETED | Модели отчётов и obligations |
| I07 | COMPLETED | POST отчёта |
| I08 | COMPLETED | Чтение и статус отчётов |
| I09 | COMPLETED | Frontend shell, MAX Bridge, initData verify |
| I10 | COMPLETED | SearchSelect и основные поля формы |
| I11 | COMPLETED | Техника и персонал |
| I12 | COMPLETED | Работы и submit |
| I13 | COMPLETED | MAX REST client, webhook handler, тесты |
| I14–I22 | WAIT | Выполняются строго по порядку |

## Текущая итерация: I14

Следующий агент делает только I14 из `08_implementation_plan.md`.

## Чек-лист I14

- [ ] Групповая/личная панель управления: backend endpoints.
- [ ] UI экраны управления.
- [ ] Тесты и lint зелёные.
- [ ] Обновлён `PROGRESS.md` и один коммит.

## HANDOFF NOTES

### 2026-07-14 — I13 завершена

**Агент:** kimi-k2.7-code:cloud  
**Ветка:** docs/max-mini-app-spec  
**Итерация:** I13 — MAX client и webhook  
**Коммит:** `<TBD>`

**Сделано:**
- Backend:
  - `app/services/max_client.py`: async REST клиент для MAX API (`/messages`, `/subscriptions`, edit, pin).
  - `app/config.py`: добавлен `max_api_base_url` (default `https://platform-api2.max.ru`).
  - `app/api/webhook.py`: `POST /api/webhook/max` с HMAC-SHA256 проверкой `x-signature` по raw payload.
  - Handlers: `bot_started` (приветствие + inline keyboard), callback `open_report` (ссылка на Mini App), callback `my_reports` (последние 5 отчётов).
  - `app/main.py`: подключён `webhook.router`.
  - Автосоздание `User` с ролью `responsible` при первом взаимодействии.
- Tests:
  - `tests/test_webhook.py`: missing/invalid signature, bot_started, callback open_report, unknown event.
  - Mock `MAXClient` через `patch`, проверяются URL/header/body без реальных HTTP.

**Проверки:**
- `make test` → 46 passed.
- `make lint` → All checks passed!

**Блокер/риск:**
- Нет.

**Следующий единственный шаг:**
- I14: групповая/личная панель управления.

**Изменённые файлы:**
- `max_daily_report/app/services/max_client.py` (new)
- `max_daily_report/app/config.py`
- `max_daily_report/app/api/webhook.py` (new)
- `max_daily_report/app/main.py`
- `max_daily_report/tests/test_webhook.py` (new)
- `docs/max-mini-app-spec/PROGRESS.md`
