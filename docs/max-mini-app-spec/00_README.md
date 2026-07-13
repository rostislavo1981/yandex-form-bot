# MAX Daily Report — пакет спецификаций MVP

## Быстрый вход

- 3 минуты: `SUMMARY.md`.
- Начать работу: `AGENT_START_HERE.md` → `PROGRESS.md` → текущая итерация в `08_implementation_plan.md`.
- Проверить решение: `DECISIONS.md`.

## Документы

| Файл | Назначение |
|---|---|
| `SUMMARY.md` | Окончательное ТЗ и приоритетный источник |
| `01_overview.md` | Пользовательский сценарий и границы |
| `02_architecture.md` | Компоненты и потоки |
| `03_data_model.md` | PostgreSQL-модель и инварианты |
| `04_api_contract.md` | REST-контракт |
| `05_max_integration.md` | MAX API, Bridge, кнопки, auth |
| `06_frontend_spec.md` | Mini App UX |
| `07_project_structure.md` | Дерево нового кода |
| `08_implementation_plan.md` | Единственный план I00–I22 |
| `09_testing_plan.md` | Автоматическая и ручная приёмка |
| `10_glossary.md` | Термины |
| `11_two_tracks.md` | Запись о закрытии выбора трека |
| `12_track_A_bot_first.md` | Заглушка для старых ссылок |
| `13_catalogs_excel.md` | Справочники, поиск, Excel import |
| `14_timesheet.md` | Табель по объектам и суммы |
| `15_group_bot.md` | Группа, пульты, scheduler |
| `PROGRESS.md` | Текущая итерация и handoff |
| `DECISIONS.md` | ADR |
| `CONVENTIONS.md` | Правила кода |

## Принято

Один продукт и один маршрут: Mini App-first + PostgreSQL + одна группа MAX + видимые кнопки + табели по объектам + Excel + reminders/morning summary.
