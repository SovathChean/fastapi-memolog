"""Telegram user domain model."""

from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.domain.base import BaseEntity


class TelegramUser(BaseEntity):
    """Telegram user entity for multi-user task management."""

    __tablename__ = "telegram_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
    )
    chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationship to tasks (one-to-many)
    tasks: Mapped[list["Task"]] = relationship(  # noqa: F821
        "Task",
        back_populates="user",
        lazy="selectin",
    )
