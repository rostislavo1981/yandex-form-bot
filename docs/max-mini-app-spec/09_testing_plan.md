# 09. План тестирования

## Автоматические уровни

- Unit: нормализация поиска, MAX initData, агрегации, Excel parsing, scheduler time.
- Integration с PostgreSQL: constraints, repos, транзакции, obligations, timesheet.
- API через ASGITransport: auth, catalogs, admin catalogs (`tests/test_admin_catalogs.py`), reports, status, imports, export.
- MAX client: только mock HTTP; реальные токены в тестах запрещены.
- Frontend: TypeScript build и минимум tests для SearchSelect/form validation и admin page API client.

## Обязательные регрессии

1. Объекты разделены в табеле.
2. Этап нельзя выбрать для чужого объекта.
3. Маш.-ч и рейсы не суммируются.
4. Переименование каталога не меняет snapshot старого отчёта.
5. Assignment на N объектов создаёт N obligations.
6. Повтор submit/webhook/scheduler не создаёт дубль.
7. Утренний список содержит ФИО и каждый несданный объект.
8. Responsible не видит чужие объекты; manager видит все.
9. Excel totals равны timesheet API.
10. Admin endpoints отклоняют `responsible`; soft-delete только деактивирует запись.

## Ручная приёмка MAX

- Бот добавлен администратором группы и может писать/закреплять.
- В группе постоянно доступен закреплённый пульт.
- В личном боте виден персональный пульт.
- `open_app` работает из обоих мест.
- После заполнения приходит одна краткая карточка.
- Reminder содержит кнопку заполнения.
- Утренняя сводка показывает правильные числа и ФИО.

## Ручная приёмка Mini App

- Поиск длинного объекта по части названия/code/alias.
- Этап фильтруется объектом.
- Несколько строк техники и работ.
- Default units и допустимые work methods.
- Ошибки сети и валидации понятны.
- Табель 31 день usable на телефоне.
- Excel скачивается по HTTPS и открывается.
- Страница `/admin/catalogs` доступна только manager/admin; добавление/редактирование/удаление строк справочников отражается в форме отчёта и Excel-экспорте.

## Команды перед handoff

Конкретные команды фиксируются в Makefile, минимум: `make lint`, `make test`, `make frontend-check`. В `PROGRESS.md` агент записывает точный вывод и число тестов.
