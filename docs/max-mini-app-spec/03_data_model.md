# 03. Модель данных

PostgreSQL 16. PK — `BIGSERIAL`; время — `TIMESTAMPTZ`; количества — `NUMERIC(14,2)`.

## Общие поля справочников

`id`, `code UNIQUE`, `name`, `search_aliases TEXT`, `active BOOLEAN`, `sort_order INT`, `created_at`, `updated_at`.

## Пользователи и MAX

### `users`

`max_user_id UNIQUE`, `full_name`, `role responsible|manager|admin`, `active`, `private_control_message_id`.

### `max_groups`

`chat_id UNIQUE`, `title`, `active`, `control_message_id`, `timezone`, часы напоминаний и утренней сводки.

### `group_members`

`group_id`, `user_id`, `active`; UNIQUE `(group_id, user_id)`.

## Справочники

- `contractors`
- `objects`: дополнительно `execution_method own|contractor`, `default_contractor_id`.
- `stages`
- `object_stages`: `(object_id, stage_id, active)`.
- `units`: дополнительно короткий символ `symbol`.
- `equipment_types`: `default_unit_id`.
- `work_types`: `default_unit_id`.
- `work_methods`.
- `work_type_methods`: допустимые способы для вида работ.

Принадлежность техники (`own`, `rented`, `contractor`) хранится в строке отчёта, а не в названии техники.

## Назначения и обязательства

### `responsible_object_assignments`

`user_id`, `object_id`, `active_from`, `active_to`, `schedule_type daily|weekdays`, `active`.

### `report_obligations`

`report_date`, `assignment_id`, `user_id`, `object_id`, `status pending|submitted|late|missed|exempt`, `due_at`, `submitted_at`, `report_id`.

UNIQUE `(report_date, assignment_id)`.

## Отчёты

### `daily_reports`

`report_date`, `responsible_user_id`, `object_id`, `stage_id`, `contractor_id`, `comment`, `staff_itr`, `staff_internal`, `staff_external`, `soil_export_m3`, `status submitted`, `idempotency_key UNIQUE`, `created_at`.

### `report_equipment`

`report_id`, `equipment_type_id`, `equipment_name_snapshot`, `ownership`, `unit_id`, `unit_name_snapshot`, `quantity`, `comment`.

### `report_works`

`report_id`, `work_type_id`, `work_name_snapshot`, `work_method_id NULL`, `method_name_snapshot NULL`, `unit_id`, `unit_name_snapshot`, `quantity`, `comment`.

## Операционные таблицы

### `notification_log`

`notification_key UNIQUE`, `kind`, `group_id`, `report_date`, `payload_json`, `status pending|sent|failed`, `attempts`, `sent_at`, `external_message_id`, `last_error`.

Примеры ключей: `reminder:2026-07-14:19:00:group-1`, `morning:2026-07-14:group-1`, `report:42:group-1`.

### `outbox_events`

`event_key UNIQUE`, `kind report_submitted|control_panel_refresh`, `payload_json`, `status pending|processing|done|failed`, `attempts`, `available_at`, `last_error`, `created_at`.

Событие `report_submitted` создаётся в той же транзакции, что отчёт. Worker публикует карточку и отмечает событие выполненным.

### `catalog_imports`

`filename`, `status uploaded|validated|applied|failed`, `summary_json`, `errors_json`, `created_by`, `created_at`, `applied_at`.

## Инварианты

1. Пользователь может отправить отчёт только по активному назначению; manager/admin могут действовать расширенно.
2. Этап должен быть связан с объектом.
3. Для contractor-объекта подрядчик обязателен.
4. Хотя бы одно из: техника, работа, грунт, персонал больше нуля.
5. Количества неотрицательны; строки техники/работ строго больше нуля.
6. Способ работы должен быть допустим для вида работы.
7. Report создаётся вместе со строками и обновлением obligation в одной транзакции.
8. Исторические отчёты не меняются при переименовании справочников.

## Табель

Табель не является отдельной таблицей. Он строится из `daily_reports`, `report_equipment`, `report_works` и `report_obligations`. Кэш/материализованное представление допускается только после измерения производительности.
