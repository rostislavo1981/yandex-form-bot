# 07. Структура проекта MVP

Новый код создаётся в подпапке `max_daily_report/`, чтобы не смешивать его с V1 `backend/`.

```text
max_daily_report/
├── pyproject.toml
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── docker-compose.prod.yml
├── Caddyfile
├── Makefile
├── README.md
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
│   │   ├── admin_catalogs.py
│   │   └── ...
│   ├── api/
│   │   ├── health.py
│   │   ├── auth.py
│   │   ├── catalogs.py
│   │   ├── admin_catalogs.py
│   │   ├── reports.py
│   │   ├── status.py
│   │   ├── timesheet.py
│   │   ├── import_export.py
│   │   ├── control_panel.py
│   │   ├── scheduler.py
│   │   └── webhook.py
│   ├── services/
│   ├── repos/
│   ├── max/
│   ├── scheduler/
│   └── seed.py
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── api/
│       │   ├── client.ts
│       │   └── admin.ts
│       ├── auth/
│       ├── pages/
│       │   ├── ReportForm.tsx
│       │   ├── Reports.tsx
│       │   ├── Timesheet.tsx
│       │   ├── SubmissionStatus.tsx
│       │   └── AdminCatalogsPage.tsx
│       ├── components/
│       │   ├── SearchSelect.tsx
│       │   ├── EquipmentRows.tsx
│       │   ├── WorkRows.tsx
│       │   └── ControlBar.tsx
│       ├── types/
│       │   └── admin.ts
│       └── hooks/
└── tests/
```

Правила границ: HTTP только в `api/` и `max/`; бизнес-правила в `services/`; SQL-запросы в `repos/`; React не знает внутреннюю схему БД; scheduler вызывает те же services.
