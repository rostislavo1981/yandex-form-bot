# 04. API-контракт MVP

Актуальность: 2026-07-15 (после FIXLIST F1–F6).

Авторизация:

- Все `/api/*`, кроме `/api/health`, `/api/webhook/max`, `/api/scheduler/*` и `/api/worker/*`, требуют заголовок `X-Init-Data` (initData из MAX Bridge). Проверка выполняется общим dependency `require_user` на каждом роутере.
- В dev (`APP_ENV=dev`) допускается `X-Init-Data: dev` — подставляется placeholder-пользователь. `DEBUG=true` этот режим **не** включает.
- `/api/scheduler/*` и `/api/worker/*` — внутренние: требуют `X-Internal-Token` = `INTERNAL_TOKEN` из env; при пустом токене доступ разрешён только в dev.
- `/api/webhook/max` — подпись `x-signature` (HMAC-SHA256 от тела с `MAX_WEBHOOK_SECRET`).

Ошибки возвращаются как `{"detail":"Сообщение по-русски"}` (или `{"detail":{"error":"..."}}` от бизнес-валидации).

## Системные endpoints

- `GET /api/health` → `{"status":"ok","version":"..."}`.
- `GET /api/auth/me` → текущий пользователь, роль, активность:

  ```json
  {
    "user": {
      "id": 1,
      "max_user_id": "max-resp-1",
      "full_name": "Иванов А. Б.",
      "role": "responsible",
      "active": true
    }
  }
  ```

- `POST /api/webhook/max` — входящий webhook от MAX. Подпись проверяется по `x-signature` (HMAC-SHA256) или официальному контракту MAX, действующему на дату реализации.

## Поисковые каталоги

Префикс `/api/catalogs`. Все поисковые endpoints принимают `q`, `limit` (default 20, max 50), `offset`. Возвращают:

```json
{"items":[{"id":42,"code":"OBJ-BOG-04","name":"Богословская КЛ 0,4 кВ"}],"total":1}
```

- `GET /api/catalogs/objects?q=` — только разрешённые пользователю объекты (manager/admin видят все; responsible — только по назначениям).
- `GET /api/catalogs/objects/{id}/stages?q=` — этапы, связанные с объектом.
- `GET /api/catalogs/equipment?q=`.
- `GET /api/catalogs/work-types?q=`.
- `GET /api/catalogs/work-types/{id}/methods` — допустимые способы для вида работы.
- `GET /api/catalogs/units` — ответ `UnitListResponse` добавляет `symbol`.
- `GET /api/catalogs/contractors?q=`.

## Admin каталоги

Префикс `/api/admin/catalogs`. Доступ: роль `manager` или `admin`. Удаление — soft-delete (`active = false`).

### Базовые справочники (CRUD + soft-delete)

Для всех ниже: `GET /`, `POST /`, `PUT /{id}`, `DELETE /{id}`.

- `/api/admin/catalogs/objects` — поля: `code`, `name`, `active`, `sort_order`, `execution_method` (`own`|`contractor`), `default_contractor_id`.
- `/api/admin/catalogs/stages` — поля: `code`, `name`, `active`, `sort_order`.
- `/api/admin/catalogs/contractors` — поля: `code`, `name`, `active`, `sort_order`.
- `/api/admin/catalogs/units` — поля: `code`, `name`, `symbol`, `active`, `sort_order`.
- `/api/admin/catalogs/equipment` — поля: `code`, `name`, `active`, `sort_order`, `default_unit_id`.
- `/api/admin/catalogs/work-types` — поля: `code`, `name`, `active`, `sort_order`, `default_unit_id`.
- `/api/admin/catalogs/work-methods` — поля: `code`, `name`, `active`, `sort_order`.

### Связные таблицы (create/delete)

- `GET /api/admin/catalogs/object-stages`
- `POST /api/admin/catalogs/object-stages` — `{"object_id": 1, "stage_id": 2, "active": true}`
- `DELETE /api/admin/catalogs/object-stages/{id}`

  Ответ списка дополняет `object_code`, `stage_code`.

- `GET /api/admin/catalogs/work-type-methods`
- `POST /api/admin/catalogs/work-type-methods` — `{"work_type_id": 1, "work_method_id": 2, "active": true}`
- `DELETE /api/admin/catalogs/work-type-methods/{id}`

  Ответ списка дополняет `work_type_code`, `work_method_code`.

### Назначения и пользователи

- `GET /api/admin/catalogs/assignments`
- `POST /api/admin/catalogs/assignments` — `{"user_id": 1, "object_id": 2, "active_from": "2026-01-01", "active_to": "2026-12-31", "schedule_type": "daily", "active": true}`
- `DELETE /api/admin/catalogs/assignments/{id}`

  Ответ списка дополняет `user_name`, `object_code`.

- `GET /api/admin/catalogs/users`
- `POST /api/admin/catalogs/users` — `{"max_user_id": "max-user-1", "full_name": "...", "role": "responsible", "active": true}`
- `PUT /api/admin/catalogs/users/{id}`
- `DELETE /api/admin/catalogs/users/{id}`

### Панели управления MAX

Префикс `/api/control-panel` (manager/admin, кроме private-ensure/refresh, доступных также responsible).

- `POST /api/control-panel/group/{group_id}/ensure` — создать/обновить и закрепить групповой пульт.
- `POST /api/control-panel/private/ensure` — создать/обновить личный пульт текущего пользователя.
- `POST /api/control-panel/group/{group_id}/refresh` — поставить в outbox задачу обновления группового пульта.
- `POST /api/control-panel/private/refresh` — обновить личный пульт.

## Отчёты

### `POST /api/reports`

Заголовок `Idempotency-Key` обязателен (повтор с тем же ключом возвращает тот же отчёт).

```json
{
  "report_date":"2026-07-14",
  "object_id":10,
  "stage_id":100,
  "contractor_id":null,
  "responsible_user_id":null,
  "staff":{"itr":1,"internal":5,"external":2},
  "soil_export_m3":24,
  "equipment":[{"equipment_type_id":7,"ownership":"own","unit_id":1,"quantity":8}],
  "works":[{"work_type_id":9,"work_method_id":2,"unit_id":3,"quantity":45}],
  "comment":"Без замечаний"
}
```

- `responsible_user_id` — опционально; заполняется только manager/admin для подачи отчёта за ответственного. Для роли responsible любое значение, кроме собственного id, отклоняется 422.
- Валидация: `staff.* >= 0`; количества строк `> 0`; отчёт обязан содержать хотя бы один факт — технику, работу, персонал или `soil_export_m3 > 0` (ноль фактом не считается); этап должен быть связан с объектом; contractor-объект требует `contractor_id`; у ответственного должно быть активное назначение на объект и дату.
- Если сдача происходит после `due_at` обязательства — obligation помечается `late` (в ответе `late:true`).

Response 201:

```json
{"id":42,"status":"submitted","late":false}
```

Response 409 — отчёт за эту дату по этому объекту уже сдан этим ответственным:

```json
{"detail":{"error":"Отчёт за эту дату по этому объекту уже сдан"}}
```

- `GET /api/reports?date_from=&date_to=&object_id=&responsible_user_id=&limit=&offset=` — список полных отчётов (responsible видит только свои; фильтр `responsible_user_id` доступен manager/admin).
- `GET /api/reports/{id}` — полный отчёт с equipment и works; responsible получает 403 на чужой отчёт.
- Изменение/удаление отчёта не входит в MVP.

## Статус сдачи

- `GET /api/submission-status?date=2026-07-14`.

```json
{
  "expected":12,
  "submitted":9,
  "late":1,
  "pending":3,
  "missing":[{"responsible":"Степанов А.","object_code":"K-25"}]
}
```

## Табель

- `GET /api/timesheet/{object_id}?date_from=&date_to=`. Объектный ID передаётся в path.

```json
{
  "object":{"id":10,"code":"BOG-KL-04","name":"Богословская КЛ 0,4 кВ"},
  "dates":["2026-07-01","2026-07-02"],
  "rows":[{
    "category":"equipment",
    "item":"Экскаватор-погрузчик · собственный",
    "unit":"маш.-ч",
    "values":[8,4],
    "total":12,
    "average":6,
    "maximum":8
  }]
}
```

- `GET /api/timesheet/{object_id}/export.xlsx?date_from=&date_to=` — экспорт табеля одного объекта.

## Excel-справочники (admin)

Префикс `/api/catalogs`.

- `GET /api/catalogs/template.xlsx` — пустой шаблон для bulk-импорта.
- `GET /api/catalogs/export.xlsx` — экспорт текущих активных справочников.
- `POST /api/catalogs/import/validate` — загрузка и preview без изменений. Возвращает `{"valid": true|false, "create": {...}, "update": {...}, "deactivate": {...}, "errors": [...]}`.
- `POST /api/catalogs/import/apply` — валидация + применение одной транзакцией. Возвращает `{"id": 1, "status": "applied", "preview": {...}, "errors": [...]}`.
- `POST /api/catalogs/import/{import_id}/apply` — **зарезервировано; не реализовано** (вернёт 501). Стадийный staged apply по ранее сохранённому `catalog_imports.id` будет добавлен позже, если потребуется отдельная кнопка «подтвердить».

Импорт напрямую без validate запрещён: `POST /api/catalogs/import/apply` сам выполняет валидацию и откатывает всё при ошибках.

## Scheduler / worker

Внутренние HTTP-эндпоинты, вызываемые контейнером scheduler или cron/healthcheck. Требуют заголовок `X-Internal-Token` (= `INTERNAL_TOKEN`); при пустом `INTERNAL_TOKEN` доступны только в dev. Каждый job держит PostgreSQL advisory lock на выделенном соединении на всё время выполнения.

- `POST /api/scheduler/morning?target_date=YYYY-MM-DD` — создать obligations на день (advisory lock).
- `POST /api/scheduler/evening-reminder?group_id=1&reminder_number=1` — вечернее напоминание (advisory lock).
- `POST /api/scheduler/morning-summary?group_id=1&target_date=YYYY-MM-DD` — утренняя сводка (advisory lock).
- `POST /api/worker/process-outbox?limit=50` — обработать pending outbox-события (карточки отчётов, обновление пультов).
