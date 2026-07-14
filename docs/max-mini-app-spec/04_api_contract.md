# 04. API-контракт MVP

Все `/api/*`, кроме `/api/health`, требуют заголовок `X-Init-Data`. Ошибка: `{"detail":"Сообщение по-русски"}`.

## Системные endpoints

- `GET /api/health` → `{"status":"ok","version":"..."}`.
- `POST /api/webhook/max` — updates MAX, защищён webhook secret по официальному контракту.
- `GET /api/auth/me` — текущий пользователь, роль, группа и назначенные объекты.

## Каталоги

Все поисковые endpoints принимают `q`, `limit` (default 20, max 50), `offset`.

- `GET /api/catalogs/objects?q=` — только разрешённые пользователю объекты.
- `GET /api/catalogs/objects/{id}/stages?q=`.
- `GET /api/catalogs/equipment?q=`.
- `GET /api/catalogs/work-types?q=&stage_id=`.
- `GET /api/catalogs/work-types/{id}/methods`.
- `GET /api/catalogs/units`.
- `GET /api/catalogs/contractors?q=`.

Ответ списка:

```json
{"items":[{"id":42,"code":"OBJ-BOG-04","name":"Богословская КЛ 0,4 кВ"}],"total":1}
```

## Admin каталоги

Доступ: роль `manager` или `admin`. Удаление — soft-delete (`active = false`).

Общий префикс: `/api/admin/catalogs`.

- `GET /api/admin/catalogs/objects` — список.
- `POST /api/admin/catalogs/objects` — создать.
- `PUT /api/admin/catalogs/objects/{id}` — обновить.
- `DELETE /api/admin/catalogs/objects/{id}` — деактивировать.

Аналогично:

- `/api/admin/catalogs/stages`
- `/api/admin/catalogs/contractors`
- `/api/admin/catalogs/units`
- `/api/admin/catalogs/equipment`
- `/api/admin/catalogs/work-types`
- `/api/admin/catalogs/work-methods`

Связные таблицы (только create/delete):

- `GET /api/admin/catalogs/object-stages`
- `POST /api/admin/catalogs/object-stages` (`object_id`, `stage_id`, `active`)
- `DELETE /api/admin/catalogs/object-stages/{id}`
- `GET /api/admin/catalogs/work-type-methods`
- `POST /api/admin/catalogs/work-type-methods` (`work_type_id`, `work_method_id`, `active`)
- `DELETE /api/admin/catalogs/work-type-methods/{id}`

Назначения и пользователи:

- `GET /api/admin/catalogs/assignments`
- `POST /api/admin/catalogs/assignments` (`user_id`, `object_id`, `active_from`, `active_to`, `schedule_type`, `active`)
- `DELETE /api/admin/catalogs/assignments/{id}`
- `GET /api/admin/catalogs/users`
- `POST /api/admin/catalogs/users` (`max_user_id`, `full_name`, `role`, `active`)
- `PUT /api/admin/catalogs/users/{id}`
- `DELETE /api/admin/catalogs/users/{id}`

## Отчёты

### `POST /api/reports`

Заголовок `Idempotency-Key` обязателен.

```json
{
  "report_date":"2026-07-14",
  "object_id":10,
  "stage_id":100,
  "contractor_id":null,
  "staff":{"itr":1,"internal":5,"external":2},
  "soil_export_m3":24,
  "equipment":[{"equipment_type_id":7,"ownership":"own","unit_id":1,"quantity":8}],
  "works":[{"work_type_id":9,"work_method_id":2,"unit_id":3,"quantity":45}],
  "comment":"Без замечаний"
}
```

Response 201: `{"id":42,"status":"submitted","late":false}`.

- `GET /api/reports?date_from=&date_to=&object_id=&responsible_user_id=&limit=&offset=`.
- `GET /api/reports/{id}` — полный отчёт.
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

- `GET /api/timesheet?object_id=10&date_from=&date_to=`.

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

- `GET /api/timesheet.xlsx?date_from=&date_to=&object_id=` — один объект или книга со всеми объектами.

## Excel-справочники (admin)

- `GET /api/catalogs/template.xlsx`.
- `GET /api/catalogs/export.xlsx`.
- `POST /api/catalogs/import/validate` — загрузка и preview без изменений.
- `POST /api/catalogs/import/{import_id}/apply` — транзакционное применение проверенного импорта.

Импорт напрямую без validate запрещён.
