"""add contracts and object_contracts

Revision ID: 8a3f2e1c4b05
Revises: b8f81b9a3983
Create Date: 2026-07-15 19:46:02.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8a3f2e1c4b05"
down_revision: str | Sequence[str] | None = "b8f81b9a3983"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "contracts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            server_onupdate=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_contracts"),
        sa.UniqueConstraint("code", name="uq_contract_code"),
    )
    op.create_index("ix_contracts_code", "contracts", ["code"], unique=True)

    op.create_table(
        "object_contracts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("object_id", sa.BigInteger(), nullable=False),
        sa.Column("contract_id", sa.BigInteger(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            server_onupdate=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"], name="fk_object_contracts_contract_id"),
        sa.ForeignKeyConstraint(["object_id"], ["objects.id"], name="fk_object_contracts_object_id"),
        sa.PrimaryKeyConstraint("id", name="pk_object_contracts"),
        sa.UniqueConstraint("object_id", "contract_id", name="uq_object_contract"),
    )
    op.create_index(
        "ix_object_contracts_object_id", "object_contracts", ["object_id"]
    )
    op.create_index(
        "ix_object_contracts_contract_id", "object_contracts", ["contract_id"]
    )

    op.add_column("daily_reports", sa.Column("contract_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_daily_reports_contract_id",
        "daily_reports",
        "contracts",
        ["contract_id"],
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_daily_reports_contract_id", "daily_reports", type_="foreignkey")
    op.drop_column("daily_reports", "contract_id")

    op.drop_index("ix_object_contracts_contract_id", table_name="object_contracts")
    op.drop_index("ix_object_contracts_object_id", table_name="object_contracts")
    op.drop_table("object_contracts")

    op.drop_index("ix_contracts_code", table_name="contracts")
    op.drop_table("contracts")
