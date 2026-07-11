"""FastAPI application factory + routes."""
from __future__ import annotations

from fastapi import FastAPI

from backend import __version__


def create_app() -> FastAPI:
    """Build the FastAPI app with health and version routes."""
    app = FastAPI(
        title="Yandex Form Bot API",
        version=__version__,
        description="Internal API for the MAX bot pipeline.",
    )

    @app.get("/healthz")
    def healthz() -> dict[str, bool | str]:
        return {"ok": True, "version": __version__}

    return app
