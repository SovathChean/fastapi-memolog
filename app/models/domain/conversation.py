"""Conversation domain model for storing chat history."""

from sqlalchemy import BigInteger, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.domain.base import BaseEntity


class ConversationMessage(BaseEntity):
    """Conversation message entity for storing Telegram chat history.

    Stores user interactions with the AI assistant for conversation
    memory and context retention across sessions.
    """

    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # "human" or "ai"
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    extra_data: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )  # Query context, intent, etc.

    __table_args__ = (
        Index(
            "idx_conversation_user_created",
            "telegram_user_id",
            "created_at",
        ),
    )

    def __repr__(self) -> str:
        """String representation of the message."""
        content_preview = (
            self.content[:50] + "..." if len(self.content) > 50 else self.content
        )
        return (
            f"<ConversationMessage(id={self.id}, "
            f"user={self.telegram_user_id}, "
            f"role={self.role}, "
            f"content='{content_preview}')>"
        )
