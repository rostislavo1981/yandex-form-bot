"""Wire the api_router into the main FastAPI app."""
from __future__ import annotations

from fastapi import FastAPI

from backend import __version__
from backend.api import api_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Yandex Form Bot API",
        version=__version__,
        description="Internal API for the MAX bot + Mini App.",
    )

    @app.get("/healthz")
    def healthz() -> dict[str, bool | str]:
        return {"ok": True, "version": __version__}

    @app.get("/")
    def root() -> dict[str, str]:
        return {"name": "yandex-form-bot", "version": __version__, "docs": "/docs"}

    app.include_router(api_router)
    return app
