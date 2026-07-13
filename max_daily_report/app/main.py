from __future__ import annotations

import uvicorn
from fastapi import FastAPI

from app.api import health
from app.config import settings


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        debug=settings.debug,
    )
    app.include_router(health.router)
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
