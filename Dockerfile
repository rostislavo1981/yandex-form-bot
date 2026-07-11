# syntax=docker/dockerfile:1.6
# Yandex Form Bot — production image
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Europe/Moscow

# System deps: curl for healthcheck, tzdata for correct cron time, tini for PID 1
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        tzdata \
        tini \
    && rm -rf /var/lib/apt/lists/* \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

# Install deps first (better cache hit rate)
COPY pyproject.toml README.md LICENSE ./
COPY backend ./backend
RUN pip install --upgrade pip && pip install -e ".[bot]"

# Chromium for Playwright (only if FORM_FILLER=real)
# Disabled by default to keep image small. Build with:
#   docker build --build-arg INSTALL_PLAYWRIGHT=1 .
ARG INSTALL_PLAYWRIGHT=0
RUN if [ "$INSTALL_PLAYWRIGHT" = "1" ]; then \
        pip install playwright && \
        playwright install --with-deps chromium; \
    fi

# Data dir (will be mounted as volume)
RUN mkdir -p /app/data/submissions

# Tiny entrypoint: pick service from CMD_ARGV or default to bot
COPY docker-entrypoint.sh /usr/local/bin/yfb-entrypoint
RUN chmod +x /usr/local/bin/yfb-entrypoint

# Healthcheck: hit /healthz if the API is up. For the bot, exit 0.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/healthz 2>/dev/null || exit 0

# tini reaps zombies and forwards signals (SIGTERM → graceful shutdown)
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/yfb-entrypoint"]

# Default: run the bot (long polling). Override in compose to run API or reminder.
CMD ["bot"]
