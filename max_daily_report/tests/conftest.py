from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

PRODUCTION_DB_SUFFIX = "mdr_db"

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://mdr_user:mdr_pass@localhost:5432/mdr_test",
)
ASYNC_TEST_DATABASE_URL = TEST_DATABASE_URL.replace(
    "postgresql+psycopg2", "postgresql+asyncpg"
)

test_engine = create_engine(TEST_DATABASE_URL, future=True)
TestSession = sessionmaker(test_engine)

async_test_engine = create_async_engine(ASYNC_TEST_DATABASE_URL, future=True, poolclass=NullPool)
AsyncTestSession = async_sessionmaker(async_test_engine, expire_on_commit=False)


def _assert_not_production_db() -> None:
    """Guard: refuse to run if connected to the production database."""
    with test_engine.connect() as conn:
        result = conn.execute(text("SELECT current_database()"))
        db_name = result.scalar()
    if not db_name:
        return
    if db_name == PRODUCTION_DB_SUFFIX:
        raise RuntimeError(
            f"Refusing to TRUNCATE production database '{db_name}'. "
            f"Set TEST_DATABASE_URL to a *_test database."
        )


@pytest.fixture(scope="function")
def db_session():
    """Provide a sync DB session for tests and rollback afterwards."""
    session = TestSession()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="function")
async def async_session():
    """Provide an async DB session for tests and rollback afterwards."""
    async with AsyncTestSession() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function", autouse=True)
def clear_tables():
    """Truncate all tables before each test to keep them independent."""
    _assert_not_production_db()
    truncate_sql = text(
        "TRUNCATE TABLE outbox_events, report_works, report_equipment, daily_reports, "
        "report_obligations, responsible_object_assignments, work_type_methods, "
        "object_stages, work_types, objects, group_members, equipment_types, "
        "work_methods, users, units, stages, max_groups, contractors, catalog_imports "
        "RESTART IDENTITY CASCADE"
    )
    with test_engine.begin() as conn:
        conn.execute(truncate_sql)
    yield
