from __future__ import annotations

import uvicorn
from fastapi import FastAPI

from app.api import catalogs, health, import_export
from app.config import settings


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        debug=settings.debug,
    )
    app.include_router(health.router)
    app.include_router(catalogs.router)
    app.include_router(import_export.router)
    return app


app = create_app()


def main() -> None:
    """CLI entry point for the API server."""
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
