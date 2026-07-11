# syntax=docker/dockerfile:1.6
# Yandex Form Bot — production image
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps for openpyxl + curl for HEALTHCHECK
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first (better cache hit rate)
COPY pyproject.toml README.md LICENSE ./
COPY backend ./backend
RUN pip install --upgrade pip && pip install -e ".[bot]"

# Chromium for Playwright (only if FORM_FILLER=real)
# Disabled by default to keep image small. Run with RUN_PLAYWRIGHT_INSTALL=1
# docker build --build-arg INSTALL_PLAYWRIGHT=1 .
ARG INSTALL_PLAYWRIGHT=0
RUN if [ "$INSTALL_PLAYWRIGHT" = "1" ]; then \
        pip install playwright && \
        playwright install --with-deps chromium; \
    fi

# Data dir (will be mounted as volume)
RUN mkdir -p /app/data/submissions

# Healthcheck: hit /healthz if the API is up
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/healthz || exit 0

# Default: run the bot (long polling). Override in compose to run API.
CMD ["python", "-m", "backend.cli.run_bot"]
