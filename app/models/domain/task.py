"""Task domain model for memolog."""

from datetime import date, datetime, time
from enum import Enum

from pgvector.sqlalchemy import Vector
from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.domain.base import BaseEntity


class TaskPeriodType(str, Enum):
    """Task period type enumeration."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class TaskStatus(str, Enum):
    """Task status enumeration."""

    PENDING = "pending"
    COMPLETED = "completed"


class TaskPriority(str, Enum):
    """Task priority enumeration."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class Task(BaseEntity):
    """Task entity for tracking daily, weekly, and monthly tasks."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("telegram_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(
        String(100), nullable=False, default="General"
    )
    period_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TaskPeriodType.DAILY.value,
    )
    period_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TaskStatus.PENDING.value,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    pending_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    completion_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(1536),
        nullable=True,
    )

    # Scheduling fields
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TaskPriority.NORMAL.value,
    )
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scheduled_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    scheduled_end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Relationship to user (many-to-one)
    user: Mapped["TelegramUser"] = relationship(  # noqa: F821
        "TelegramUser",
        back_populates="tasks",
    )
