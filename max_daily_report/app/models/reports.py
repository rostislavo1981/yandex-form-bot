from __future__ import annotations

from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ResponsibleObjectAssignment(Base):
    __tablename__ = "responsible_object_assignments"
    __table_args__ = (
        UniqueConstraint("user_id", "object_id", name="uq_responsible_assignment"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    object_id: Mapped[int] = mapped_column(ForeignKey("objects.id"), nullable=False)
    active_from: Mapped[Date] = mapped_column(Date, nullable=False)
    active_to: Mapped[Date] = mapped_column(Date, nullable=False)
    schedule_type: Mapped[str] = mapped_column(
        Enum("daily", "weekdays", name="assignment_schedule_type"),
        nullable=False,
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


class ReportObligation(Base):
    __tablename__ = "report_obligations"
    __table_args__ = (
        UniqueConstraint("report_date", "assignment_id", name="uq_obligation_date_assignment"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    report_date: Mapped[Date] = mapped_column(Date, nullable=False)
    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("responsible_object_assignments.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    object_id: Mapped[int] = mapped_column(ForeignKey("objects.id"), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(
            "pending",
            "submitted",
            "late",
            "missed",
            "exempt",
            name="report_obligation_status",
        ),
        default="pending",
        nullable=False,
    )
    due_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    submitted_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    report_id: Mapped[int | None] = mapped_column(
        ForeignKey("daily_reports.id"), nullable=True
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    assignment: Mapped[ResponsibleObjectAssignment] = relationship()


class DailyReport(Base):
    __tablename__ = "daily_reports"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_daily_report_idempotency_key"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    report_date: Mapped[Date] = mapped_column(Date, nullable=False)
    responsible_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    object_id: Mapped[int] = mapped_column(ForeignKey("objects.id"), nullable=False)
    stage_id: Mapped[int] = mapped_column(ForeignKey("stages.id"), nullable=False)
    contractor_id: Mapped[int | None] = mapped_column(
        ForeignKey("contractors.id"), nullable=True
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    staff_itr: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    staff_internal: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    staff_external: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    soil_export_m3: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    status: Mapped[str] = mapped_column(
        Enum("submitted", name="daily_report_status"),
        default="submitted",
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    equipment: Mapped[list[ReportEquipment]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    works: Mapped[list[ReportWork]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ReportEquipment(Base):
    __tablename__ = "report_equipment"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("daily_reports.id"), nullable=False
    )
    equipment_type_id: Mapped[int] = mapped_column(
        ForeignKey("equipment_types.id"), nullable=False
    )
    equipment_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    ownership: Mapped[str] = mapped_column(
        Enum("own", "rented", "contractor", name="equipment_ownership"),
        nullable=False,
    )
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id"), nullable=False)
    unit_name_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    report: Mapped[DailyReport] = relationship(back_populates="equipment")


class ReportWork(Base):
    __tablename__ = "report_works"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("daily_reports.id"), nullable=False
    )
    work_type_id: Mapped[int] = mapped_column(
        ForeignKey("work_types.id"), nullable=False
    )
    work_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    work_method_id: Mapped[int | None] = mapped_column(
        ForeignKey("work_methods.id"), nullable=True
    )
    method_name_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id"), nullable=False)
    unit_name_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    report: Mapped[DailyReport] = relationship(back_populates="works")


class NotificationLog(Base):
    __tablename__ = "notification_log"
    __table_args__ = (UniqueConstraint("notification_key", name="uq_notification_key"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    notification_key: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    group_id: Mapped[int | None] = mapped_column(
        ForeignKey("max_groups.id"), nullable=True
    )
    report_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("pending", "sent", "failed", name="notification_status"),
        default="pending",
        nullable=False,
    )
    attempts: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    sent_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    external_message_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (UniqueConstraint("event_key", name="uq_outbox_event_key"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_key: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(
        Enum(
            "report_submitted",
            "control_panel_refresh",
            name="outbox_event_kind",
        ),
        nullable=False,
    )
    payload_json: Mapped[dict | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(
            "pending",
            "processing",
            "done",
            "failed",
            name="outbox_event_status",
        ),
        default="pending",
        nullable=False,
    )
    attempts: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    available_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
