"""Repository for Telegram user data access."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.telegram_user import TelegramUser
from app.repositories.base import SQLAlchemyRepository


class TelegramUserRepository(SQLAlchemyRepository[TelegramUser]):
    """Repository for Telegram user CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async SQLAlchemy session.
        """
        super().__init__(session, TelegramUser)

    async def get_by_telegram_id(
        self, telegram_id: int, bot_type: str = "memolog"
    ) -> TelegramUser | None:
        """Get user by Telegram ID and bot type.

        Args:
            telegram_id: Telegram user ID (from update.effective_user.id).
            bot_type: Bot identifier (memolog, crypto, etc.).

        Returns:
            TelegramUser if found, None otherwise.
        """
        query = select(TelegramUser).where(
            TelegramUser.telegram_id == telegram_id,
            TelegramUser.bot_type == bot_type,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        telegram_id: int,
        bot_type: str = "memolog",
        chat_id: int | None = None,
        username: str | None = None,
        first_name: str = "User",
        last_name: str | None = None,
        language_code: str | None = None,
    ) -> tuple[TelegramUser, bool]:
        """Get existing user or create new one.

        Args:
            telegram_id: Telegram user ID.
            bot_type: Bot identifier (memolog, crypto, etc.).
            chat_id: Chat ID for messaging.
            username: Telegram @username.
            first_name: User's first name.
            last_name: User's last name.
            language_code: User's language code.

        Returns:
            Tuple of (TelegramUser, created) where created is True if new user.
        """
        # Try to find existing user
        existing = await self.get_by_telegram_id(telegram_id, bot_type)
        if existing:
            # Update user info if changed
            updated = False
            if chat_id and existing.chat_id != chat_id:
                existing.chat_id = chat_id
                updated = True
            if username and existing.username != username:
                existing.username = username
                updated = True
            if first_name and existing.first_name != first_name:
                existing.first_name = first_name
                updated = True
            if last_name and existing.last_name != last_name:
                existing.last_name = last_name
                updated = True
            if language_code and existing.language_code != language_code:
                existing.language_code = language_code
                updated = True

            if updated:
                await self.session.flush()
                await self.session.refresh(existing)

            return existing, False

        # Create new user
        new_user = TelegramUser(
            telegram_id=telegram_id,
            bot_type=bot_type,
            chat_id=chat_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
            is_active=True,
        )
        created_user = await self.insert(new_user)
        return created_user, True

    async def deactivate_user(
        self, telegram_id: int, bot_type: str = "memolog"
    ) -> bool:
        """Deactivate a user by Telegram ID and bot type.

        Args:
            telegram_id: Telegram user ID.
            bot_type: Bot identifier (memolog, crypto, etc.).

        Returns:
            True if user was deactivated, False if not found.
        """
        user = await self.get_by_telegram_id(telegram_id, bot_type)
        if user:
            user.is_active = False
            await self.session.flush()
            return True
        return False
