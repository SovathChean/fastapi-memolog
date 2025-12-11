"""Base handler abstract class for Telegram commands."""

import logging
from abc import ABC, abstractmethod

from telegram import Update
from telegram.ext import ContextTypes


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
