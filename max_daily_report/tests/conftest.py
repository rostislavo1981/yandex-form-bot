from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://mdr_user:mdr_pass@localhost:5432/mdr_db",
)

test_engine = create_engine(TEST_DATABASE_URL, future=True)
TestSession = sessionmaker(test_engine)


@pytest.fixture(scope="function", autouse=True)
def db_session():
    """Provide a sync DB session for tests and rollback afterwards."""
    session = TestSession()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="function", autouse=True)
def clear_tables():
    """Truncate all tables before each test to keep them independent."""
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
