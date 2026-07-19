"""add short/full title to objects

Revision ID: a3f4c5d6e7f8
Revises: b8f81b9a3983
Create Date: 2026-07-19 14:30:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "a3f4c5d6e7f8"
down_revision: str | None = "b8f81b9a3983"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("objects", sa.Column("short_title", sa.String(length=255), nullable=True))
    op.add_column("objects", sa.Column("full_title", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("objects", "full_title")
    op.drop_column("objects", "short_title")
