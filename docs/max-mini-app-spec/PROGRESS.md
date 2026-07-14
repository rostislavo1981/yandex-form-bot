# PROGRESS

Обновлено: 2026-07-14.

## Текущий статус

I14 завершена. Групповой/личный пульт управления.

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
| I14 | COMPLETED | Групповой/личный пульт управления |
| I15–I22 | WAIT | Выполняются строго по порядку |

## Текущая итерация: I15

Следующий агент делает только I15 из `08_implementation_plan.md`.

## Чек-лист I15

- [ ] Outbox event `report_submitted` создаётся в транзакции отчёта.
- [ ] Worker публикует краткую карточку в группу с кнопками retry.
- [ ] Notification key `report:{report_id}:{group_id}` предотвращает дубли.
- [ ] Временная ошибка MAX оставляет retry.
- [ ] Карточка содержит объект, ФИО, итоги.
- [ ] Тесты и lint зелёные.
- [ ] Обновлён `PROGRESS.md` и один коммит.

## HANDOFF NOTES

### 2026-07-14 — I14 завершена

**Агент:** kimi-k2.7-code:cloud  
**Ветка:** docs/max-mini-app-spec  
**Итерация:** I14 — Видимые пульты  
**Коммит:** `<TBD>`

**Сделано:**
- Backend:
  - `app/services/control_panel_service.py`: `ensure_group_control_panel`, `ensure_private_control_panel`, `refresh_group_panel_outbox`, `record_notification`.
  - `app/api/control_panel.py`: endpoints `POST /api/control-panel/group/{id}/ensure`, `POST /api/control-panel/private/ensure`, `POST /api/control-panel/group/{id}/refresh`, `POST /api/control-panel/private/refresh` с role-based доступом.
  - `app/main.py`: подключён `control_panel.router`.
  - Групповой пульт: создаётся/обновляется, закрепляется, хранит `control_message_id`.
  - Личный пульт: восстанавливается `/start` и `/menu` (через webhook + API), хранит `private_control_message_id`.
  - Повторный вызов редактирует существующее сообщение вместо создания нового.
- Tests:
  - `tests/test_control_panel.py`: auth, role checks, manager ensure, private refresh, outbox scheduling.

**Проверки:**
- `make test` → 51 passed.
- `make lint` → All checks passed!

**Блокер/риск:**
- Нет.

**Следующий единственный шаг:**
- I15: карточка после отчёта.

**Изменённые файлы:**
- `max_daily_report/app/services/control_panel_service.py` (new)
- `max_daily_report/app/api/control_panel.py` (new)
- `max_daily_report/app/main.py`
- `max_daily_report/tests/test_control_panel.py` (new)
- `docs/max-mini-app-spec/PROGRESS.md`
