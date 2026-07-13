from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CatalogMixin


class Contractor(Base, CatalogMixin):
    __tablename__ = "contractors"


class Object(Base, CatalogMixin):
    __tablename__ = "objects"

    execution_method: Mapped[str | None] = mapped_column(
        Enum("own", "contractor", name="object_execution_method"),
        nullable=True,
    )
    default_contractor_id: Mapped[int | None] = mapped_column(
        ForeignKey("contractors.id"), nullable=True
    )

    default_contractor: Mapped[Contractor] = relationship(foreign_keys=[default_contractor_id])


class Stage(Base, CatalogMixin):
    __tablename__ = "stages"


class ObjectStage(Base):
    __tablename__ = "object_stages"
    __table_args__ = (UniqueConstraint("object_id", "stage_id", name="uq_object_stage"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    object_id: Mapped[int] = mapped_column(ForeignKey("objects.id"), nullable=False)
    stage_id: Mapped[int] = mapped_column(ForeignKey("stages.id"), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    object: Mapped[Object] = relationship()
    stage: Mapped[Stage] = relationship()


class Unit(Base, CatalogMixin):
    __tablename__ = "units"

    symbol: Mapped[str] = mapped_column(String(16), nullable=False)


class EquipmentType(Base, CatalogMixin):
    __tablename__ = "equipment_types"

    default_unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("units.id"), nullable=True
    )

    default_unit: Mapped[Unit] = relationship()


class WorkType(Base, CatalogMixin):
    __tablename__ = "work_types"

    default_unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("units.id"), nullable=True
    )

    default_unit: Mapped[Unit] = relationship()


class WorkMethod(Base, CatalogMixin):
    __tablename__ = "work_methods"


class WorkTypeMethod(Base):
    __tablename__ = "work_type_methods"
    __table_args__ = (
        UniqueConstraint("work_type_id", "work_method_id", name="uq_work_type_method"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    work_type_id: Mapped[int] = mapped_column(ForeignKey("work_types.id"), nullable=False)
    work_method_id: Mapped[int] = mapped_column(
        ForeignKey("work_methods.id"), nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    work_type: Mapped[WorkType] = relationship()
    work_method: Mapped[WorkMethod] = relationship()
