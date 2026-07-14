from __future__ import annotations

import uvicorn
from fastapi import FastAPI, Request
from sqlalchemy import select

from app.api import auth, catalogs, health, import_export, reports, webhook
from app.config import settings
from app.database import AsyncSessionLocal
from app.models.users import User


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        debug=settings.debug,
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(catalogs.router)
    app.include_router(import_export.router)
    app.include_router(reports.router)
    app.include_router(reports.submission_router)
    app.include_router(webhook.router)

    @app.middleware("http")
    async def dev_user_middleware(request: Request, call_next):
        """Attach a real dev placeholder user for dev-only auth."""
        is_dev = settings.debug or settings.app_env == "dev"
        is_api = request.url.path.startswith("/api/") and not request.url.path.startswith("/api/health")
        if is_api and is_dev:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(User).where(User.max_user_id == "dev-user")
                )
                user = result.scalar_one_or_none()
                if user is None:
                    user = User(
                        max_user_id="dev-user",
                        full_name="Dev User",
                        role="responsible",
                    )
                    session.add(user)
                    await session.commit()
                    await session.refresh(user)
                request.state.user = user
        return await call_next(request)

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
