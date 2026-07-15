# MAX Daily Report — пакет спецификаций MVP

## Быстрый вход

- 3 минуты: `SUMMARY.md`.
- Начать работу: `AGENT_START_HERE.md` → `PROGRESS.md` → текущая итерация в `REMEDIATION_PLAN.md`.
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
| `06_frontend_spec.md` | Mini App UX, включая `/admin/catalogs` |
| `07_project_structure.md` | Дерево нового кода |
| `08_implementation_plan.md` | Исторический план завершённых I00–I22 |
| `REMEDIATION_PLAN.md` | Завершённый план исправлений R00–R14 (R15 blocked) |
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

## Статус

- **R00–R14:** ✅ Выполнены
- **R15:** 🚫 Заблокирован (требует реальный MAX токен/домен)
- **Тесты:** 151 backend + 10 frontend
- **CI:** GitHub Actions настроен
