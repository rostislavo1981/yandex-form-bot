# 07. Полная структура проекта

Имя корневой директории: `max_daily_report/`.

```
max_daily_report/
├── README.md                     # квик-старт
├── .env.example                  # шаблон переменных
├── .gitignore
├── .dockerignore
├── docker-compose.yml            # dev
├── docker-compose.prod.yml       # prod (Caddy + HTTPS)
├── Caddyfile                     # конфиг Caddy для prod
├── nginx.conf                    # конфиг nginx для dev (или Caddy dev)
├── Makefile                      # шорткаты (make up / make test)
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pyproject.toml
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI: create_app(), lifespan, routers
│   │   ├── bot.py                # entry-point long polling: python -m app.bot
│   │   ├── config.py             # Settings (pydantic-settings)
│   │   ├── database.py           # engine, session, Base, get_db
│   │   ├── models.py             # SQLAlchemy models (см. 03_data_model.md)
│   │   ├── schemas.py            # Pydantic-схемы req/resp
│   │   ├── seed.py               # начальные данные
│   │   ├── webapp_auth.py        # verify_init_data + dependency require_max_user
│   │   ├── deps.py               # FastAPI Depends helpers
│   │   ├── errors.py             # исключения приложения
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── health.py         # /api/health
│   │   │   ├── bootstrap.py      # /api/bootstrap
│   │   │   ├── reports.py        # /api/reports*
│   │   │   ├── summary.py        # /api/summary
│   │   │   └── export.py         # /api/export.xlsx
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── report_service.py # бизнес-логика создания отчёта
│   │   │   ├── summary_service.py
│   │   │   └── excel_service.py  # openpyxl построение
│   │   ├── repos/
│   │   │   ├── __init__.py
│   │   │   ├── report_repo.py
│   │   │   ├── user_repo.py
│   │   │   └── dict_repo.py      # справочники
│   │   └── max/
│   │       ├── __init__.py
│   │       ├── client.py         # MaxClient (httpx) — sendMessage, getUpdates
│   │       ├── handlers.py       # обработчики команд
│   │       └── poller.py         # цикл long polling
│   └── tests/
│       ├── conftest.py           # pgtest fixture
│       ├── test_health.py
│       ├── test_bootstrap.py
│       ├── test_reports_create.py
│       ├── test_reports_list.py
│       ├── test_summary.py
│       ├── test_export_xlsx.py
│       ├── test_webapp_auth.py
│       └── test_max_client.py    # с mock httpx
│
├── frontend/
│   ├── Dockerfile                # multi-stage: build → nginx static
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api.ts
│       ├── auth.ts
│       ├── contexts/
│       │   └── BootstrapContext.tsx
│       ├── pages/
│       │   ├── ReportForm.tsx
│       │   └── Summary.tsx
│       ├── components/
│       │   ├── EquipmentRow.tsx
│       │   ├── WorkRow.tsx
│       │   ├── StaffBlock.tsx
│       │   ├── SummaryCard.tsx
│       │   └── Banner.tsx
│       ├── hooks/
│       │   └── useReport.ts
│       └── styles/
│           └── main.css
│
├── deploy/
│   ├── install.sh                # bootstrap на чистом VPS
│   └── systemd/
│       └── max-daily-report.service   # если без docker
│
├── scripts/
│   ├── reset_db.sh
│   └── load_seed.sh
│
└── docs/
    ├── 01_overview.md            # копия из этого пакета
    ├── 02_architecture.md
    ├── 03_data_model.md
    ├── 04_api_contract.md
    ├── 05_max_integration.md
    ├── 06_frontend_spec.md
    ├── 07_project_structure.md
    ├── 08_implementation_plan.md
    ├── 09_testing_plan.md
    └── 10_glossary.md
```

## Назначение ключевых файлов

### backend/app/main.py
- `create_app()` собирает FastAPI, роутеры, CORS, middleware.
- `lifespan`: create tables + seed, если пусто.
- Экспортирует `app` для uvicorn.

### backend/app/bot.py
- Точка входа `python -m app.bot`.
- Читает `Settings`, создаёт `MaxClient`, запускает `poller.run()`.

### backend/app/config.py
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_env: str = "dev"                # dev | prod
    database_url: str
    max_bot_token: str = ""
    max_api_base: str = "https://api.max.ru"    # [непроверено]
    webapp_public_url: str = "http://localhost:8080"
    cors_origins: list[str] = ["http://localhost:8080"]
    internal_token: str = "change-me"

    class Config:
        env_file = ".env"
```

### backend/app/database.py
- `engine = create_async_engine(settings.database_url)`
- `SessionLocal = async_sessionmaker(...)`
- `async def get_db()` — dependency.

### backend/app/max/client.py
```python
class MaxClient:
    def __init__(self, token: str, base: str):
        self.token = token
        self.base = f"{base}/bot{token}"

    async def get_updates(self, offset: int, timeout: int = 25) -> list[dict]:
        ...
    async def send_message(self, chat_id: int, text: str, reply_markup: dict | None = None) -> dict:
        ...
    async def set_my_commands(self, cmds: list[dict]) -> None:
        ...
```

### frontend/vite.config.ts
```ts
export default {
  server: {
    port: 5173,
    proxy: { "/api": "http://backend:8000" }
  },
  build: { outDir: "dist" }
}
```

## .env.example
```
APP_ENV=dev
DATABASE_URL=postgresql+asyncpg://mvp:mvp@db:5432/mvp
MAX_BOT_TOKEN=
MAX_API_BASE=https://api.max.ru
WEBAPP_PUBLIC_URL=http://localhost:8080
CORS_ORIGINS=["http://localhost:8080"]
INTERNAL_TOKEN=change-me-please
```

## Makefile
```
.PHONY: up down build logs test lint reset

up:      docker compose up -d
down:    docker compose down
build:   docker compose build
logs:    docker compose logs -f
test:    docker compose exec backend pytest -v
lint:    docker compose exec backend ruff check .
reset:   docker compose down -v && docker compose up -d --build
```
