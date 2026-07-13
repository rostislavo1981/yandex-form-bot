# 07. Структура проекта MVP

Новый код создаётся в подпапке `max_daily_report/`, чтобы не смешивать его с V1 `backend/`.

```text
max_daily_report/
├── pyproject.toml
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── Caddyfile
├── Makefile
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── deps.py
│   ├── models/
│   │   ├── catalogs.py
│   │   ├── users.py
│   │   ├── reports.py
│   │   └── operations.py
│   ├── schemas/
│   ├── api/
│   │   ├── health.py
│   │   ├── auth.py
│   │   ├── catalogs.py
│   │   ├── reports.py
│   │   ├── status.py
│   │   ├── timesheet.py
│   │   └── import_export.py
│   ├── services/
│   │   ├── catalog_service.py
│   │   ├── report_service.py
│   │   ├── obligation_service.py
│   │   ├── notification_service.py
│   │   ├── timesheet_service.py
│   │   └── excel_service.py
│   ├── repos/
│   ├── max/
│   │   ├── client.py
│   │   ├── auth.py
│   │   ├── keyboards.py
│   │   ├── handlers.py
│   │   └── webhook.py
│   ├── scheduler/
│   │   ├── main.py
│   │   └── jobs.py
│   └── seed.py
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── api.ts
│       ├── auth.ts
│       ├── pages/
│       │   ├── ReportForm.tsx
│       │   ├── Reports.tsx
│       │   ├── Timesheet.tsx
│       │   └── SubmissionStatus.tsx
│       └── components/
│           ├── SearchSelect.tsx
│           ├── EquipmentRows.tsx
│           ├── WorkRows.tsx
│           └── ControlBar.tsx
├── templates/catalogs.xlsx
└── tests/
```

Правила границ: HTTP только в `api/` и `max/`; бизнес-правила в `services/`; SQL-запросы в `repos/`; React не знает внутреннюю схему БД; scheduler вызывает те же services.
