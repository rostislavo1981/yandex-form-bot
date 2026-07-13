from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for FastAPI dependency injection."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
