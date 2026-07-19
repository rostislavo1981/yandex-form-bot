.PHONY: help install lint test db-up db-down api clean restore-smoke

PY := /usr/bin/env -u PYTHONPATH ../.venv/bin/python
PIP := /usr/bin/env -u PYTHONPATH ../.venv/bin/pip
RUFF := /usr/bin/env -u PYTHONPATH ../.venv/bin/ruff
PYTEST := /usr/bin/env -u PYTHONPATH ../.venv/bin/pytest
UVICORN := /usr/bin/env -u PYTHONPATH ../.venv/bin/uvicorn

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

install: ## Install package + dev deps into .venv
	@test -d ../.venv || python3 -m venv ../.venv
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	@test -f .env || cp .env.example .env && echo "Created .env from template — fill in secrets!"

lint: ## Run ruff linter
	$(RUFF) check .

test: ## Run pytest against test DB (localhost:5432)
	TEST_DATABASE_URL=postgresql+psycopg2://mdr_user:mdr_pass@localhost:5432/mdr_test DATABASE_URL=postgresql+asyncpg://mdr_user:mdr_pass@localhost:5432/mdr_test $(PYTEST) -q

db-up: ## Start PostgreSQL in Docker
	docker compose up -d db

db-down: ## Stop Docker services
	docker compose down

api: ## Run FastAPI dev server
	$(UVICORN) app.main:app --host 0.0.0.0 --port 8000 --reload

prod-up: ## Start production stack (migrations + services)
	docker compose -f docker-compose.prod.yml up -d db
	@echo "Waiting for PostgreSQL..."
	@until docker compose -f docker-compose.prod.yml exec -T db pg_isready -U ${POSTGRES_USER:-mdr_user} -d ${POSTGRES_DB:-mdr_db} 2>/dev/null; do sleep 1; done
	./scripts/migrate.sh
	docker compose -f docker-compose.prod.yml up -d

prod-down: ## Stop production stack
	docker compose -f docker-compose.prod.yml down

prod-logs: ## Tail production logs
	docker compose -f docker-compose.prod.yml logs -f

migrate: ## Run Alembic migrations in production
	./scripts/migrate.sh

backup: ## Backup PostgreSQL to BACKUP_DIR
	./scripts/backup.sh

restore-smoke: ## Restore the newest backup into a temporary DB and remove it
	./scripts/restore-smoke.sh

frontend-check: ## Build frontend and run frontend tests
	cd frontend && npm run build && npm run test

clean: ## Remove caches, build artifacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache build dist *.egg-info
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
