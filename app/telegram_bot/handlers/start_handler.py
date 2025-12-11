"""Handler for /start and /help commands."""

from telegram import Update
from telegram.ext import ContextTypes

from app.support.telegram_support import TelegramSupport
from app.telegram_bot.handlers.base import BaseHandler


class StartHandler(BaseHandler):
    """Handler for start and help commands."""

    def __init__(self) -> None:
        """Initialize the handler."""
        super().__init__()
        self.telegram_support = TelegramSupport()

    @property
    def commands(self) -> list[str]:
        """Commands this handler responds to."""
        return ["start", "help"]

    async def handle(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /start and /help commands.

        Args:
            update: Telegram update object.
            context: Callback context.
        """
        help_text = self.telegram_support.format_help()
        await self.send_message(update, help_text)
