from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine

from tests.conftest import _assert_not_production_db


class TestDatabaseGuard:
    def test_guard_rejects_production_database(self):
        engine = create_engine(
            "postgresql+psycopg2://mdr_user:mdr_pass@localhost:5432/mdr_db",
            future=True,
        )
        with patch("tests.conftest.test_engine", engine):
            with pytest.raises(RuntimeError, match="Refusing to TRUNCATE production"):
                _assert_not_production_db()

    def test_guard_accepts_test_database(self):
        engine = create_engine(
            "postgresql+psycopg2://mdr_user:mdr_pass@localhost:5432/mdr_test",
            future=True,
        )
        with patch("tests.conftest.test_engine", engine):
            _assert_not_production_db()

    def test_default_url_points_to_test_db(self):
        url = os.environ.get(
            "TEST_DATABASE_URL",
            "postgresql+psycopg2://mdr_user:mdr_pass@localhost:5432/mdr_test",
        )
        assert url.endswith("mdr_test"), f"Default TEST_DATABASE_URL must end with mdr_test, got: {url}"
