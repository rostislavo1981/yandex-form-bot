# 13. Динамические справочники и Excel

## Источник истины

PostgreSQL — источник истины. Excel — транспорт для массового изменения.

## Web-админка `/admin/catalogs`

Доступ: `manager` и `admin`. Экран в Mini App содержит табы:

- Объекты
- Этапы
- Подрядчики
- Единицы измерения
- Техника
- Виды работ
- Способы работ
- Этапы объектов
- Способы видов работ
- Назначения
- Пользователи

Каждая таблица поддерживает inline-добавление, inline-редактирование и soft-delete (`active=false`).

Кнопки в тулбаре:

- **Экспорт Excel** — скачивает `/api/catalogs/export.xlsx`.
- **Шаблон Excel** — скачивает пустой `/api/catalogs/template.xlsx`.
- **Импорт** — upload `.xlsx` в `/api/catalogs/import/apply` (validate + apply одним запросом). Прямой вызов `/api/catalogs/import/validate` остаётся доступен для preview; staged apply по `import_id` зарезервирован.

Админ-страница не заменяет Excel bulk-загрузку, а дополняет её быстрым поштучным редактированием.

## Шаблон

Листы: `Users`, `Objects`, `Stages`, `ObjectStages`, `Contractors`, `Units`, `Equipment`, `WorkTypes`, `WorkMethods`, `WorkTypeMethods`, `Assignments`.

Обязательные служебные колонки: `code`, `name`, `active`, `sort_order`. Связи задаются по code, не по отображаемому имени.

## Импорт

1. Upload сохраняет запись `catalog_imports`.
2. Validate читает все листы, нормализует пробелы, проверяет обязательные колонки, дубли code, ссылки и enum.
3. Backend возвращает preview: create/update/deactivate/errors.
4. `POST /api/catalogs/import/apply` выполняет validate и upsert одной транзакцией.
5. Ошибка откатывает весь импорт.
6. Staged apply по ранее сохранённому `import_id` (`POST /api/catalogs/import/{import_id}/apply`) зарезервирован и не реализован.

Отсутствующая строка не деактивируется автоматически. Для деактивации нужно `active=0`.

## Поиск

Индексировать `lower(code || ' ' || name || ' ' || search_aliases)` с `pg_trgm`. Нормализовать `ё/е`, дефисы и повторные пробелы. Сортировка: точное совпадение code, начало слова, similarity, sort_order.

## История

Удаление справочников запрещено, только `active=false`. Отчёты хранят FK и snapshot-названия.
