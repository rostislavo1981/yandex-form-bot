.PHONY: help install lint test run bot api clean

PY := /usr/bin/env -u PYTHONPATH .venv/bin/python
PIP := /usr/bin/env -u PYTHONPATH .venv/bin/pip
RUFF := /usr/bin/env -u PYTHONPATH .venv/bin/ruff
PYTEST := /usr/bin/env -u PYTHONPATH .venv/bin/pytest

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

install: ## Install package + dev deps into .venv
	@test -d .venv || python3 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	@test -f .env || cp .env.example .env && echo "Created .env from template — fill in secrets!"

lint: ## Run ruff linter
	$(RUFF) check .

test: ## Run pytest
	$(PYTEST) -q

api: ## Run FastAPI dev server
	$(PY) -m backend.cli.run_api

bot: ## Run MAX bot (long polling)
	$(PY) -m backend.cli.run_bot

run: api ## alias for api

clean: ## Remove caches, venv, build artifacts
	rm -rf .venv .pytest_cache .ruff_cache .mypy_cache build dist *.egg-info
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
