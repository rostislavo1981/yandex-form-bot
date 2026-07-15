"""add report name snapshots to daily_reports

Revision ID: c4d5e6f7a8b9
Revises: 8a3f2e1c4b05
Create Date: 2026-07-15 22:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a8b9"
down_revision: str | Sequence[str] | None = "8a3f2e1c4b05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "daily_reports",
        sa.Column(
            "object_name_snapshot",
            sa.String(length=255),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "daily_reports",
        sa.Column("contract_code_snapshot", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "daily_reports",
        sa.Column("contract_full_name_snapshot", sa.String(length=255), nullable=True),
    )
    # drop the server_default once existing rows are backfilled with empty string
    op.alter_column("daily_reports", "object_name_snapshot", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("daily_reports", "contract_full_name_snapshot")
    op.drop_column("daily_reports", "contract_code_snapshot")
    op.drop_column("daily_reports", "object_name_snapshot")
