from __future__ import annotations

from sqlalchemy import BigInteger, DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CatalogImport(Base):
    __tablename__ = "catalog_imports"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("uploaded", "validated", "applied", "failed", name="catalog_import_status"),
        default="uploaded",
        nullable=False,
    )
    summary_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    errors_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    applied_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    @property
    def summary(self) -> dict | None:
        return self.summary_json

    @summary.setter
    def summary(self, value: dict | None) -> None:
        self.summary_json = value

    @property
    def errors(self) -> list | None:
        return self.errors_json

    @errors.setter
    def errors(self, value: list | None) -> None:
        self.errors_json = value
