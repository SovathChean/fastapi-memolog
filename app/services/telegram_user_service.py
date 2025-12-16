"""Service for managing Telegram users."""

from app.models.domain.telegram_user import TelegramUser
from app.repositories.telegram_user_repository import TelegramUserRepository
from app.services.base import BaseService


class TelegramUserService(BaseService):
    """Service for Telegram user management operations."""

    def __init__(self, repository: TelegramUserRepository) -> None:
        """Initialize service with repository.

        Args:
            repository: TelegramUserRepository instance.
        """
        super().__init__()
        self.repository = repository

    async def get_or_create_user(
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

        This method is called on every Telegram interaction to ensure
        the user exists in our database.

        Args:
            telegram_id: Telegram user ID (from update.effective_user.id).
            bot_type: Bot identifier (memolog, crypto, etc.).
            chat_id: Chat ID for sending messages.
            username: Telegram @username.
            first_name: User's first name.
            last_name: User's last name.
            language_code: User's language code.

        Returns:
            Tuple of (TelegramUser, created) where created is True if new.
        """
        user, created = await self.repository.get_or_create(
            telegram_id=telegram_id,
            bot_type=bot_type,
            chat_id=chat_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
        )

        if created:
            uname = username or "no_username"
            self.logger.info(f"Created new Telegram user: {telegram_id} (@{uname})")
        else:
            self.logger.debug(f"Found existing Telegram user: {telegram_id}")

        return user, created

    async def get_by_telegram_id(
        self, telegram_id: int, bot_type: str = "memolog"
    ) -> TelegramUser | None:
        """Get user by their Telegram ID and bot type.

        Args:
            telegram_id: Telegram user ID.
            bot_type: Bot identifier (memolog, crypto, etc.).

        Returns:
            TelegramUser if found, None otherwise.
        """
        return await self.repository.get_by_telegram_id(telegram_id, bot_type)

    async def deactivate_user(
        self, telegram_id: int, bot_type: str = "memolog"
    ) -> bool:
        """Deactivate a user (e.g., when they block the bot).

        Args:
            telegram_id: Telegram user ID.
            bot_type: Bot identifier (memolog, crypto, etc.).

        Returns:
            True if user was deactivated, False if not found.
        """
        result = await self.repository.deactivate_user(telegram_id, bot_type)
        if result:
            self.logger.info(f"Deactivated Telegram user: {telegram_id}")
        return result
