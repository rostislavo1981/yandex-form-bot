# 03. Модель данных

Все таблицы — PostgreSQL 16. SQL-типы указаны в скобках. Первичные ключи — `BIGSERIAL`.

## Таблицы

### `users`
Пользователи бота (прорабы, руководители).

| Поле | Тип | Ограничения | Комментарий |
|---|---|---|---|
| `id` | BIGSERIAL | PK | |
| `max_user_id` | VARCHAR(64) | UNIQUE NOT NULL | ID из MAX (строка) |
| `full_name` | VARCHAR(200) | NOT NULL | Отображаемое имя |
| `role` | VARCHAR(20) | NOT NULL, DEFAULT 'foreman' | `foreman` \| `manager` \| `admin` |
| `active` | BOOLEAN | NOT NULL, DEFAULT true | |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

### `contractors`
Подрядные организации.

| Поле | Тип | Ограничения |
|---|---|---|
| `id` | BIGSERIAL | PK |
| `name` | VARCHAR(250) | UNIQUE NOT NULL |
| `active` | BOOLEAN | NOT NULL, DEFAULT true |

### `objects`
Строительные объекты. **Центральная сущность.**

| Поле | Тип | Ограничения | Комментарий |
|---|---|---|---|
| `id` | BIGSERIAL | PK | |
| `title_code` | VARCHAR(50) | UNIQUE NOT NULL | Уникальный титул, напр. `БОГ-КЛ-04` |
| `name` | VARCHAR(250) | NOT NULL | Полное имя |
| `execution_method` | VARCHAR(20) | NOT NULL | `own` \| `contractor` |
| `default_contractor_id` | BIGINT | FK contractors.id NULL | Только если method=contractor |
| `active` | BOOLEAN | NOT NULL, DEFAULT true | |

**Правило:** если `execution_method='contractor'`, то `default_contractor_id IS NOT NULL` (CHECK).

### `stages`
Этапы работ на объекте.

| Поле | Тип | Ограничения |
|---|---|---|
| `id` | BIGSERIAL | PK |
| `object_id` | BIGINT | FK objects.id, NOT NULL, ON DELETE CASCADE |
| `name` | VARCHAR(250) | NOT NULL |
| `active` | BOOLEAN | NOT NULL, DEFAULT true |

`UNIQUE (object_id, name)`.

### `units`
Единицы измерения.

| Поле | Тип |
|---|---|
| `id` | BIGSERIAL PK |
| `name` | VARCHAR(50) UNIQUE NOT NULL |
| `code` | VARCHAR(20) UNIQUE NOT NULL |

Seed: `машино-час/mch`, `метр/m`, `м³/m3`, `штука/pcs`, `тонна/t`, `смена/shift`.

### `equipment`
Справочник техники.

| Поле | Тип |
|---|---|
| `id` | BIGSERIAL PK |
| `category` | VARCHAR(100) NOT NULL |
| `name` | VARCHAR(250) UNIQUE NOT NULL |
| `default_unit_id` | BIGINT FK units.id NOT NULL |
| `active` | BOOLEAN NOT NULL DEFAULT true |

### `work_types`
Справочник видов работ.

| Поле | Тип |
|---|---|
| `id` | BIGSERIAL PK |
| `category` | VARCHAR(100) NOT NULL |
| `name` | VARCHAR(250) UNIQUE NOT NULL |
| `default_unit_id` | BIGINT FK units.id NOT NULL |
| `active` | BOOLEAN NOT NULL DEFAULT true |

### `daily_reports`
Шапка ежедневного отчёта.

| Поле | Тип | Комментарий |
|---|---|---|
| `id` | BIGSERIAL PK | |
| `report_date` | DATE NOT NULL | Дата отчёта |
| `responsible_user_id` | BIGINT FK users.id NOT NULL | Кто сдал |
| `object_id` | BIGINT FK objects.id NOT NULL | |
| `stage_id` | BIGINT FK stages.id NOT NULL | |
| `contractor_id` | BIGINT FK contractors.id NULL | Обязателен если object.execution_method=contractor |
| `comment` | TEXT NULL | |
| `staff_itr` | INT NOT NULL DEFAULT 0 | Только для own |
| `staff_internal` | INT NOT NULL DEFAULT 0 | Только для own |
| `staff_external` | INT NOT NULL DEFAULT 0 | Только для own |
| `soil_export_m3` | NUMERIC(12,2) NOT NULL DEFAULT 0 | Вывоз грунта |
| `status` | VARCHAR(20) NOT NULL DEFAULT 'submitted' | MVP: только `submitted` |
| `created_at` | TIMESTAMPTZ NOT NULL DEFAULT now() | |

Индексы: `(report_date DESC)`, `(responsible_user_id, report_date)`, `(object_id, report_date)`.

**CHECK:** `stage_id` должен принадлежать `object_id` (проверяется в API, не в CHECK — так проще).

### `report_equipment`
Строки техники в отчёте.

| Поле | Тип |
|---|---|
| `id` | BIGSERIAL PK |
| `report_id` | BIGINT FK daily_reports.id NOT NULL, ON DELETE CASCADE |
| `equipment_id` | BIGINT FK equipment.id NOT NULL |
| `equipment_name_snapshot` | VARCHAR(250) NOT NULL |
| `unit_id` | BIGINT FK units.id NOT NULL |
| `quantity` | NUMERIC(12,2) NOT NULL CHECK (quantity > 0) |
| `ownership` | VARCHAR(20) NOT NULL | `own` \| `rented` \| `contractor` |
| `comment` | TEXT NULL |

### `report_works`
Строки выполненных работ.

| Поле | Тип |
|---|---|
| `id` | BIGSERIAL PK |
| `report_id` | BIGINT FK daily_reports.id NOT NULL, ON DELETE CASCADE |
| `work_type_id` | BIGINT FK work_types.id NOT NULL |
| `work_name_snapshot` | VARCHAR(250) NOT NULL |
| `unit_id` | BIGINT FK units.id NOT NULL |
| `quantity` | NUMERIC(12,2) NOT NULL CHECK (quantity > 0) |
| `method` | VARCHAR(100) NULL | «открытый», «ГНБ», «вручную» |
| `comment` | TEXT NULL |

## Snapshot-поля

`equipment_name_snapshot` и `work_name_snapshot` копируют текущее имя справочника в момент сохранения. Если справочник позже переименуют/деактивируют — исторические отчёты сохраняют то, что реально было.

## Seed-данные (для первого запуска)

**users:**
- `Казнадеев И.` (foreman, `max_user_id="dev-1"`)
- `Иванов П.` (manager, `max_user_id="dev-2"`)

**contractors:**
- `ООО "СтройМонтаж"`
- `ООО "БКТП-Сервис"`

**objects:**
- `БОГ-КЛ-04 | Богословская КЛ 04кВ` (own)
- `РСТИ-БКТП-3 | БКТП №3 Тамбасова` (contractor, default: БКТП-Сервис)

**stages:**
- БОГ-КЛ-04: `Разработка траншеи`, `Прокладка кабеля`, `Обратная засыпка`
- РСТИ-БКТП-3: `Монтаж БКТП`, `Пусконаладка`

**equipment:**
- `Землеройная / Экскаватор-погрузчик / машино-час`
- `Землеройная / Экскаватор гусеничный / машино-час`
- `Грузовая / Самосвал / машино-час`
- `Подъёмная / Автокран / машино-час`

**work_types:**
- `Земляные работы / Разработка траншеи / метр`
- `Кабельные работы / Прокладка кабеля / метр`
- `Земляные работы / Обратная засыпка / м³`
- `Монтаж / Установка БКТП / штука`

Seed запускается один раз при старте, если таблица `users` пустая.

## Инварианты (проверяются в API)

1. `stage.object_id == report.object_id`.
2. `object.execution_method == 'contractor' ⟹ report.contractor_id IS NOT NULL`.
3. `object.execution_method == 'own' ⟹ report.contractor_id IS NULL` (или игнорируется).
4. Хотя бы одно из: `equipment_rows`, `work_rows`, `soil_export_m3 > 0`.
5. Все `quantity > 0`.
6. Все `staff_* >= 0`.
7. `unit_id` для строк должен существовать в `units`.

## SQL-миграция начального состояния

Оформляется как `backend/app/db/schema.sql` или через `Base.metadata.create_all()`. Alembic вводится в Phase 5.
