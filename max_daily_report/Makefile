.PHONY: help install lint test db-up db-down api clean

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

test: ## Run pytest
	$(PYTEST) -q

db-up: ## Start PostgreSQL in Docker
	docker compose up -d db

db-down: ## Stop Docker services
	docker compose down

api: ## Run FastAPI dev server
	$(UVICORN) app.main:app --host 0.0.0.0 --port 8000 --reload

clean: ## Remove caches, build artifacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache build dist *.egg-info
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
