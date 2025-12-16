"""Base handler for crypto bot commands."""

import logging
from abc import ABC, abstractmethod

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from app.models.domain.telegram_user import TelegramUser
from app.repositories.telegram_user_repository import TelegramUserRepository
from app.services.telegram_user_service import TelegramUserService


class BaseCryptoHandler(ABC):
    """Abstract base class for crypto bot command handlers."""

    def __init__(self) -> None:
        """Initialize the handler."""
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    @abstractmethod
    def commands(self) -> list[str]:
        """Commands this handler responds to."""
        pass

    @abstractmethod
    async def handle(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle the command.

        Args:
            update: Telegram update object.
            context: Callback context.
        """
        pass

    def get_command_name(self, update: Update) -> str:
        """Extract command name from update."""
        if not update.message or not update.message.text:
            return ""

        text = update.message.text
        if text.startswith("/"):
            return text.split()[0][1:].split("@")[0]
        return ""

    def get_command_args(self, update: Update) -> str:
        """Extract command arguments from update."""
        if not update.message or not update.message.text:
            return ""

        text = update.message.text
        parts = text.split(maxsplit=1)
        return parts[1] if len(parts) > 1 else ""

    async def send_message(
        self,
        update: Update,
        text: str,
        parse_mode: str = "HTML",
    ) -> None:
        """Send a message to the chat."""
        if update.message:
            await update.message.reply_text(text, parse_mode=parse_mode)

    async def send_typing(self, update: Update) -> None:
        """Send typing action to indicate bot is processing."""
        if update.message:
            await update.message.chat.send_action(ChatAction.TYPING)

    async def get_or_create_user(
        self,
        update: Update,
        session,
    ) -> TelegramUser:
        """Get or create the Telegram user from update."""
        if not update.effective_user:
            raise ValueError("No user in update")

        telegram_user = update.effective_user
        repository = TelegramUserRepository(session)
        service = TelegramUserService(repository)

        user, created = await service.get_or_create_user(
            telegram_id=telegram_user.id,
            bot_type="crypto",
            chat_id=update.effective_chat.id if update.effective_chat else None,
            username=telegram_user.username,
            first_name=telegram_user.first_name or "Unknown",
            last_name=telegram_user.last_name,
            language_code=telegram_user.language_code,
        )

        if created:
            self.logger.info(f"Created new crypto user: {user.telegram_id}")

        return user
