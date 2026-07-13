# 04. API контракт

Базовый URL: `https://<domain>/api` (prod), `http://localhost:8080/api` (dev).

Все запросы к защищённым эндпоинтам обязаны содержать заголовок:
```
X-Auth-InitData: <строка initData от MAX>
```
Исключения: `/api/health`.

Content-Type для POST: `application/json`.

Все даты — ISO 8601 (`YYYY-MM-DD`). Числа — JSON number.

## Общие ошибки

| Код | Когда |
|---|---|
| 400 | Валидация не прошла (тело / бизнес-правила) |
| 401 | Нет/невалидный `X-Auth-InitData` |
| 403 | Пользователь не имеет права (напр. чужой отчёт) |
| 404 | Ресурс не найден |
| 422 | Ошибка Pydantic-схемы |
| 500 | Внутренняя ошибка |

Формат ошибки:
```json
{"detail": "Читаемое сообщение по-русски"}
```
или Pydantic:
```json
{"detail": [{"loc": ["body", "quantity"], "msg": "must be > 0", "type": "value_error"}]}
```

---

## `GET /api/health`

Без авторизации. Liveness.

**Response 200:**
```json
{"status": "ok", "version": "0.1.0"}
```

---

## `GET /api/bootstrap`

Возвращает все справочники одним запросом. Кэшируется на клиенте.

**Response 200:**
```json
{
  "current_user": {
    "id": 1,
    "full_name": "Казнадеев И.",
    "role": "foreman",
    "max_user_id": "dev-1"
  },
  "users": [
    {"id": 1, "full_name": "Казнадеев И.", "role": "foreman"}
  ],
  "objects": [
    {
      "id": 10,
      "title_code": "БОГ-КЛ-04",
      "name": "Богословская КЛ 04кВ",
      "execution_method": "own",
      "default_contractor_id": null
    },
    {
      "id": 11,
      "title_code": "РСТИ-БКТП-3",
      "name": "БКТП №3 Тамбасова",
      "execution_method": "contractor",
      "default_contractor_id": 20
    }
  ],
  "stages": [
    {"id": 100, "object_id": 10, "name": "Разработка траншеи"},
    {"id": 101, "object_id": 10, "name": "Прокладка кабеля"},
    {"id": 200, "object_id": 11, "name": "Монтаж БКТП"}
  ],
  "contractors": [
    {"id": 20, "name": "ООО \"БКТП-Сервис\""}
  ],
  "units": [
    {"id": 1, "name": "машино-час", "code": "mch"},
    {"id": 2, "name": "метр", "code": "m"},
    {"id": 3, "name": "м³", "code": "m3"}
  ],
  "equipment": [
    {"id": 1000, "category": "Землеройная", "name": "Экскаватор-погрузчик", "default_unit_id": 1}
  ],
  "work_types": [
    {"id": 2000, "category": "Земляные работы", "name": "Разработка траншеи", "default_unit_id": 2}
  ]
}
```

Отдаются только записи с `active=true`.

---

## `POST /api/reports`

Создать отчёт.

**Request:**
```json
{
  "report_date": "2026-07-13",
  "responsible_user_id": 1,
  "object_id": 10,
  "stage_id": 100,
  "contractor_id": null,
  "comment": "Работа шла в штатном режиме",
  "staff_itr": 1,
  "staff_internal": 3,
  "staff_external": 2,
  "soil_export_m3": 24.5,
  "equipment_rows": [
    {
      "equipment_id": 1000,
      "unit_id": 1,
      "quantity": 8,
      "ownership": "own",
      "comment": null
    }
  ],
  "work_rows": [
    {
      "work_type_id": 2000,
      "unit_id": 2,
      "quantity": 45,
      "method": "открытый",
      "comment": null
    }
  ]
}
```

**Response 201:**
```json
{"id": 42, "status": "submitted"}
```

**Правила валидации** (см. `03_data_model.md` §Инварианты).

**Response 400** (пример):
```json
{"detail": "Этап 200 не принадлежит объекту 10"}
```

---

## `GET /api/reports`

Список отчётов.

**Query:**
- `date_from`: `YYYY-MM-DD` (по умолчанию: сегодня минус 7 дней)
- `date_to`: `YYYY-MM-DD` (по умолчанию: сегодня)
- `object_id`: int (опц.)
- `responsible_user_id`: int (опц.)
- `mine`: `true|false` (если true — только свои по `max_user_id`)
- `limit`: int, default 100, max 500
- `offset`: int, default 0

**Response 200:**
```json
{
  "total": 12,
  "items": [
    {
      "id": 42,
      "report_date": "2026-07-13",
      "object": {"id": 10, "title_code": "БОГ-КЛ-04", "name": "Богословская КЛ 04кВ"},
      "stage": {"id": 100, "name": "Разработка траншеи"},
      "responsible": {"id": 1, "full_name": "Казнадеев И."},
      "contractor": null,
      "status": "submitted",
      "created_at": "2026-07-13T18:24:11Z"
    }
  ]
}
```

---

## `GET /api/reports/{id}`

Полный отчёт со строками.

**Response 200:**
```json
{
  "id": 42,
  "report_date": "2026-07-13",
  "responsible": {"id": 1, "full_name": "Казнадеев И."},
  "object": {"id": 10, "title_code": "БОГ-КЛ-04", "name": "Богословская КЛ 04кВ", "execution_method": "own"},
  "stage": {"id": 100, "name": "Разработка траншеи"},
  "contractor": null,
  "comment": "Работа шла в штатном режиме",
  "staff": {"itr": 1, "internal": 3, "external": 2},
  "soil_export_m3": 24.5,
  "equipment_rows": [
    {
      "id": 300,
      "equipment_id": 1000,
      "name": "Экскаватор-погрузчик",
      "unit": {"id": 1, "name": "машино-час"},
      "quantity": 8,
      "ownership": "own",
      "comment": null
    }
  ],
  "work_rows": [
    {
      "id": 400,
      "work_type_id": 2000,
      "name": "Разработка траншеи",
      "unit": {"id": 2, "name": "метр"},
      "quantity": 45,
      "method": "открытый",
      "comment": null
    }
  ],
  "status": "submitted",
  "created_at": "2026-07-13T18:24:11Z"
}
```

---

## `GET /api/summary`

Агрегаты за период (для главного экрана сводной).

**Query:** `date_from`, `date_to` (обязательны).

**Response 200:**
```json
{
  "date_from": "2026-07-13",
  "date_to": "2026-07-13",
  "count": 5,
  "totals": {
    "soil_export_m3": 120.5,
    "staff_total": 34,
    "machine_hours": 42
  },
  "by_object": [
    {"object_id": 10, "title_code": "БОГ-КЛ-04", "reports": 3, "soil_export_m3": 80.5}
  ]
}
```

---

## `GET /api/export.xlsx`

Excel-выгрузка. Query: `date_from`, `date_to` (опц., по умолчанию — весь период).

**Response 200:** `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, `Content-Disposition: attachment; filename=reports_2026-07-13.xlsx`.

**Листы:**
1. `Реестр отчётов` — по одной строке на отчёт (шапка).
2. `Техника` — по одной строке на `report_equipment`.
3. `Работы` — по одной строке на `report_works`.

---

## `POST /api/bot/notify` (внутренний, не для Mini App)

Позволяет backend'у попросить bot отправить сообщение прорабу. Защищён shared secret'ом в заголовке `X-Internal-Token`.

**Request:**
```json
{"max_user_id": "dev-1", "text": "✅ Отчёт №42 принят"}
```
**Response 200:** `{"ok": true}`.

В MVP можно **не реализовывать** — Mini App показывает успех прямо в webview.
