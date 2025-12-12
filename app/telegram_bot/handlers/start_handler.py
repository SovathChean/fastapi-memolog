"""Handler for /start and /help commands."""

from telegram import Update
from telegram.ext import ContextTypes

from app.support.telegram_support import TelegramSupport
from app.telegram_bot.handlers.base import BaseHandler
from config.database import get_session_factory


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
        # Store/update user in database on /start or /help
        session_factory = get_session_factory()
        async with session_factory() as session:
            await self.get_or_create_user(update, session)
            await session.commit()

        # Send help text
        help_text = self.telegram_support.format_help()
        await self.send_message(update, help_text)
