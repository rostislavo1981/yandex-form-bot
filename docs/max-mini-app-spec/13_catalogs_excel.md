# 13. Динамические справочники и Excel

## Источник истины

PostgreSQL — источник истины. Excel — транспорт для массового изменения.

## Шаблон

Листы: `Users`, `Objects`, `Stages`, `ObjectStages`, `Contractors`, `Units`, `Equipment`, `WorkTypes`, `WorkMethods`, `WorkTypeMethods`, `Assignments`.

Обязательные служебные колонки: `code`, `name`, `active`, `sort_order`. Связи задаются по code, не по отображаемому имени.

## Импорт

1. Upload сохраняет запись `catalog_imports`.
2. Validate читает все листы, нормализует пробелы, проверяет обязательные колонки, дубли code, ссылки и enum.
3. Backend возвращает preview: create/update/deactivate/errors.
4. Только отдельный Apply выполняет upsert одной транзакцией.
5. Ошибка откатывает весь импорт.

Отсутствующая строка не деактивируется автоматически. Для деактивации нужно `active=0`.

## Поиск

Индексировать `lower(code || ' ' || name || ' ' || search_aliases)` с `pg_trgm`. Нормализовать `ё/е`, дефисы и повторные пробелы. Сортировка: точное совпадение code, начало слова, similarity, sort_order.

## История

Удаление справочников запрещено, только `active=false`. Отчёты хранят FK и snapshot-названия.
