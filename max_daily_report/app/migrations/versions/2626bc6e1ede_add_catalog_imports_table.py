"""add catalog_imports table

Revision ID: 2626bc6e1ede
Revises: 1a2e795e0f06
Create Date: 2026-07-14 01:02:51.249987

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "2626bc6e1ede"
down_revision: str | None = "1a2e795e0f06"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("DROP TYPE IF EXISTS catalog_import_status CASCADE")
    op.create_table(
        "catalog_imports",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.Enum("uploaded", "validated", "applied", "failed", name="catalog_import_status"),
            nullable=False,
        ),
        sa.Column("summary_json", JSONB(), nullable=True),
        sa.Column("errors_json", JSONB(), nullable=True),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("catalog_imports")
    op.execute("DROP TYPE IF EXISTS catalog_import_status CASCADE")
