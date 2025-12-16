"""Base handler abstract class for Telegram commands."""

import logging
from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from app.models.domain.telegram_user import TelegramUser
from app.repositories.telegram_user_repository import TelegramUserRepository
from app.services.telegram_user_service import TelegramUserService


class BaseHandler(ABC):
    """Abstract base class for all Telegram command handlers.

    All command handlers must inherit from this class and implement
    the required abstract methods.
    """

    def __init__(self) -> None:
        """Initialize the handler with a logger."""
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    @abstractmethod
    def commands(self) -> list[str]:
        """List of command names this handler responds to.

        Returns:
            List of command strings (without the leading /).
        """
        pass

    @abstractmethod
    async def handle(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle the incoming command.

        Args:
            update: Telegram update object.
            context: Callback context from python-telegram-bot.
        """
        pass

    async def send_message(
        self,
        update: Update,
        text: str,
        parse_mode: str = "HTML",
    ) -> None:
        """Send a message to the chat.

        Args:
            update: Telegram update object.
            text: Message text to send.
            parse_mode: Message parse mode (HTML, Markdown, etc.).
        """
        if update.effective_chat:
            await update.effective_chat.send_message(
                text=text,
                parse_mode=parse_mode,
            )

    async def send_typing(self, update: Update) -> None:
        """Show typing indicator to user.

        Call this before long-running operations (AI calls, searches)
        to indicate the bot is processing the request.

        Args:
            update: Telegram update object.
        """
        if update.effective_chat:
            await update.effective_chat.send_action(ChatAction.TYPING)

    def get_command_args(self, update: Update) -> str:
        """Extract arguments from a command message.

        Args:
            update: Telegram update object.

        Returns:
            Arguments string after the command.
        """
        if update.message and update.message.text:
            parts = update.message.text.split(maxsplit=1)
            return parts[1] if len(parts) > 1 else ""
        return ""

    def get_command_name(self, update: Update) -> str:
        """Extract the command name from a message.

        Args:
            update: Telegram update object.

        Returns:
            Command name without the leading /.
        """
        if update.message and update.message.text:
            text = update.message.text.strip()
            if text.startswith("/"):
                return text.split()[0][1:].lower()
        return ""

    async def get_or_create_user(
        self,
        update: Update,
        session: AsyncSession,
    ) -> TelegramUser:
        """Get or create a TelegramUser from the update.

        This should be called at the start of each handler to ensure
        we have a valid user record for the current Telegram user.

        Args:
            update: Telegram update object.
            session: Database session.

        Returns:
            TelegramUser instance.

        Raises:
            ValueError: If no effective user in update.
        """
        if not update.effective_user:
            raise ValueError("No effective user in update")

        telegram_user = update.effective_user
        repository = TelegramUserRepository(session)
        service = TelegramUserService(repository)

        user, created = await service.get_or_create_user(
            telegram_id=telegram_user.id,
            bot_type="memolog",
            chat_id=update.effective_chat.id if update.effective_chat else None,
            username=telegram_user.username,
            first_name=telegram_user.first_name or "User",
            last_name=telegram_user.last_name,
            language_code=telegram_user.language_code,
        )

        if created:
            self.logger.info(f"Created new user: {user.telegram_id}")

        return user
