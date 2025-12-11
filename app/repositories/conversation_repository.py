"""Conversation repository for chat history persistence."""

from fastapi import Depends
from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.conversation import ConversationMessage
from app.repositories.base import SQLAlchemyRepository
from config.database import get_db


class ConversationRepository(SQLAlchemyRepository[ConversationMessage]):
    """Repository for ConversationMessage entity database operations.

    Extends base repository with conversation-specific queries including
    user history retrieval and message management.
    """

    def __init__(self, session: AsyncSession = Depends(get_db)):
        """Initialize repository with database session.

        Args:
            session: Async database session.
        """
        super().__init__(session, ConversationMessage)

    async def get_user_history(
        self,
        telegram_user_id: int,
        limit: int = 10,
    ) -> list[ConversationMessage]:
        """Get recent conversation history for a user.

        Args:
            telegram_user_id: Telegram user ID.
            limit: Maximum messages to return.

        Returns:
            List of messages ordered by creation time (oldest first).
        """
        stmt = (
            select(ConversationMessage)
            .where(ConversationMessage.telegram_user_id == telegram_user_id)
            .order_by(ConversationMessage.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        messages = list(result.scalars().all())
        # Reverse to get chronological order
        return list(reversed(messages))

    async def add_message(
        self,
        telegram_user_id: int,
        role: str,
        content: str,
        extra_data: dict | None = None,
    ) -> ConversationMessage:
        """Add a new message to conversation history.

        Args:
            telegram_user_id: Telegram user ID.
            role: Message role ('human' or 'ai').
            content: Message content.
            extra_data: Optional extra data dict.

        Returns:
            Created message entity.
        """
        message = ConversationMessage(
            telegram_user_id=telegram_user_id,
            role=role,
            content=content,
            extra_data=extra_data,
        )
        return await self.insert(message)

    async def add_exchange(
        self,
        telegram_user_id: int,
        human_message: str,
        ai_message: str,
        extra_data: dict | None = None,
    ) -> tuple[ConversationMessage, ConversationMessage]:
        """Add a human-AI message exchange.

        Args:
            telegram_user_id: Telegram user ID.
            human_message: User's message content.
            ai_message: AI's response content.
            extra_data: Optional extra data for both messages.

        Returns:
            Tuple of (human_message, ai_message) entities.
        """
        human = await self.add_message(
            telegram_user_id=telegram_user_id,
            role="human",
            content=human_message,
            extra_data=extra_data,
        )
        ai = await self.add_message(
            telegram_user_id=telegram_user_id,
            role="ai",
            content=ai_message,
            extra_data=extra_data,
        )
        return human, ai

    async def clear_user_history(
        self,
        telegram_user_id: int,
    ) -> int:
        """Clear all conversation history for a user.

        Args:
            telegram_user_id: Telegram user ID.

        Returns:
            Number of deleted messages.
        """
        stmt = delete(ConversationMessage).where(
            ConversationMessage.telegram_user_id == telegram_user_id
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def get_message_count(
        self,
        telegram_user_id: int,
    ) -> int:
        """Get total message count for a user.

        Args:
            telegram_user_id: Telegram user ID.

        Returns:
            Number of messages.
        """
        return await self.count(telegram_user_id=telegram_user_id)

    async def trim_old_messages(
        self,
        telegram_user_id: int,
        keep_count: int = 20,
    ) -> int:
        """Trim old messages, keeping only the most recent ones.

        Args:
            telegram_user_id: Telegram user ID.
            keep_count: Number of recent messages to keep.

        Returns:
            Number of deleted messages.
        """
        # Get IDs of messages to keep
        keep_stmt = (
            select(ConversationMessage.id)
            .where(ConversationMessage.telegram_user_id == telegram_user_id)
            .order_by(ConversationMessage.created_at.desc())
            .limit(keep_count)
        )
        keep_result = await self.session.execute(keep_stmt)
        keep_ids = [row[0] for row in keep_result.all()]

        if not keep_ids:
            return 0

        # Delete messages not in keep list
        delete_stmt = delete(ConversationMessage).where(
            and_(
                ConversationMessage.telegram_user_id == telegram_user_id,
                ConversationMessage.id.notin_(keep_ids),
            )
        )
        result = await self.session.execute(delete_stmt)
        await self.session.flush()
        return result.rowcount
