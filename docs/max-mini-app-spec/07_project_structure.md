# 07. Структура проекта MVP

Новый код создаётся в подпапке `max_daily_report/`, чтобы не смешивать его с V1 `backend/`.

```text
max_daily_report/
├── pyproject.toml          # Python package + dev deps
├── .env.example            # Все обязательные переменные
├── .env                    # Локальные секреты (не в git)
├── Dockerfile              # Multi-stage: backend + собранный frontend
├── docker-compose.yml      # Локальная PostgreSQL
├── docker-compose.prod.yml # app + scheduler + db + caddy
├── Caddyfile               # HTTPS reverse proxy
├── Makefile                # lint, test, db-up, api, prod-up, backup...
├── README.md               # Quickstart и production runbook
├── alembic.ini             # Настройки миграций
├── app/
│   ├── main.py             # FastAPI factory, SPA fallback, dev middleware
│   ├── config.py           # Pydantic Settings
│   ├── database.py         # async engine + AsyncSessionLocal
│   ├── deps.py             # FastAPI Depends(get_session)
│   ├── scheduler_runner.py # APScheduler: obligations / reminders / summary
│   ├── seed.py             # Идемпотентный seed каталогов и назначений
│   ├── models/
│   │   ├── base.py         # Base, CatalogMixin
│   │   ├── catalogs.py     # Object, Stage, Unit, WorkType, WorkMethod и связи
│   │   ├── users.py        # User, MaxGroup, GroupMember
│   │   ├── reports.py      # DailyReport, ReportEquipment, ReportWork, ResponsibleObjectAssignment, ReportObligation
│   │   └── operations.py   # NotificationLog, OutboxEvent, CatalogImport
│   ├── schemas/
│   │   ├── admin_catalogs.py
│   │   ├── catalogs.py
│   │   ├── reports.py
│   │   └── users.py
│   ├── api/
│   │   ├── health.py
│   │   ├── auth.py              # /auth/me + MAX initData validation + dev fallback
│   │   ├── catalogs.py          # Поисковые catalog endpoints
│   │   ├── admin_catalogs.py    # CRUD /api/admin/catalogs
│   │   ├── reports.py           # POST/GET отчётов + submission_router /api/submission-status
│   │   ├── timesheet.py         # /api/timesheet/{object_id}
│   │   ├── import_export.py     # /api/catalogs/template.xlsx, export.xlsx, import/apply
│   │   ├── control_panel.py     # /api/control-panel/*
│   │   ├── scheduler.py         # /api/scheduler/*
│   │   ├── webhook.py           # /api/webhook/max
│   │   └── worker.py            # /api/worker/process-outbox
│   ├── services/
│   │   ├── catalog_service.py
│   │   ├── report_service.py
│   │   ├── obligation_service.py
│   │   ├── timesheet_service.py
│   │   ├── timesheet_excel_service.py
│   │   ├── excel_service.py
│   │   ├── control_panel_service.py
│   │   ├── notification_worker.py
│   │   ├── scheduler_service.py
│   │   └── max_client.py
│   ├── repos/
│   │   └── catalogs.py
│   └── migrations/         # Alembic versions
│       ├── env.py
│       └── versions/
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig*.json
│   ├── .env.production     # VITE_ALLOW_DEV_AUTH=true только для локального Docker
│   └── src/
│       ├── App.tsx
│       ├── main.tsx
│       ├── api/
│       │   ├── client.ts
│       │   ├── auth.ts
│       │   ├── catalogs.ts
│       │   ├── reports.ts
│       │   ├── timesheet.ts
│       │   └── admin.ts
│       ├── bridge/
│       │   └── index.ts
│       ├── pages/
│       │   ├── ReportPage.tsx
│       │   ├── ReportsPage.tsx
│       │   ├── TimesheetPage.tsx
│       │   ├── StatusPage.tsx
│       │   └── AdminCatalogsPage.tsx
│       ├── components/
│       │   ├── SearchSelect.tsx
│       │   ├── EquipmentRows.tsx
│       │   ├── WorkRows.tsx
│       │   ├── PersonnelField.tsx
│       │   ├── ErrorState.tsx
│       │   ├── Loading.tsx
│       │   └── Layout.tsx
│       ├── hooks/
│       │   ├── useAuth.ts
│       │   └── useDebounce.ts
│       ├── types/
│       │   ├── admin.ts
│       │   ├── catalogs.ts
│       │   ├── reports.ts
│       │   └── index.ts
│       └── test/
│           ├── setup.ts
│           ├── auth.test.ts
│           ├── SearchSelect.test.tsx
│           ├── EquipmentRows.test.tsx
│           ├── WorkRows.test.tsx
│           ├── PersonnelField.test.tsx
│           └── Layout.test.tsx
├── scripts/
│   ├── migrate.sh
│   ├── backup.sh
│   └── register_webhook.sh
├── tests/
│   ├── conftest.py
│   ├── test_admin_catalogs.py
│   ├── test_auth.py
│   ├── test_catalogs.py
│   ├── test_control_panel.py
│   ├── test_database.py
│   ├── test_excel_apply.py
│   ├── test_excel_validate.py
│   ├── test_health.py
│   ├── test_notification_worker.py
│   ├── test_obligations.py
│   ├── test_reports.py
│   ├── test_scheduler.py
│   ├── test_seed.py
│   ├── test_timesheet.py
│   ├── test_timesheet_excel.py
│   └── test_webhook.py
└── backups/                # Локальные pg_dump (в .gitignore)
```

## Правила границ

- HTTP / request handling — только в `app/api/` и `app/max/`.
- Бизнес-правила и координация транзакций — в `app/services/`.
- SQL-запросы и ORM-утилиты — в `app/repos/`.
- Схемы Pydantic — в `app/schemas/`, маршруты ссылаются на них, но не на модели БД.
- React не знает внутреннюю схему БД; типы frontend централизованы в `frontend/src/types/`.
- Scheduler вызывает те же `services`, что и API; не дублирует бизнес-логику.
