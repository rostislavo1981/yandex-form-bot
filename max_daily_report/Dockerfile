# syntax=docker/dockerfile:1.6

# Stage 1: build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    TZ=Europe/Moscow

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

COPY certs/*.crt /usr/local/share/ca-certificates/
RUN update-ca-certificates

COPY pyproject.toml ./
COPY app ./app
COPY --from=frontend-builder /frontend/dist ./app/static
COPY alembic.ini ./
RUN pip install --upgrade pip --disable-pip-version-check && pip install -e "."

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/health 2>/dev/null || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Stage 3: Backend test (based on production base)
FROM base AS backend-test

COPY pyproject.toml ./
COPY app ./app
COPY --from=frontend-builder /frontend/dist ./app/static
COPY alembic.ini ./
COPY tests ./tests

RUN pip install --upgrade pip --disable-pip-version-check && pip install -e ".[dev]"

CMD ["sh", "-c", "alembic upgrade head && pytest -q"]

# Stage 4: Frontend test
FROM node:20-alpine AS frontend-test
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
CMD ["sh", "-c", "npm run test && npm run build"]
