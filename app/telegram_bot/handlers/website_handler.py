"""Website handler for showing login URL."""

from telegram import Update
from telegram.ext import ContextTypes

from app.telegram_bot.handlers.base import BaseHandler


class WebsiteHandler(BaseHandler):
    """Handler for /website command to show login URL."""

    @property
    def commands(self) -> list[str]:
        """Return list of commands this handler responds to."""
        return ["website"]

    async def handle(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle the /website command.

        Args:
            update: Telegram update object.
            context: Callback context from python-telegram-bot.
        """
        await self.send_message(
            update,
            "🌐 <b>Memolog Web Dashboard</b>\n\n"
            "📊 View and manage your tasks in real-time!\n\n"
            "✨ <b>Features:</b>\n"
            "• 📋 See all your tasks at a glance\n"
            "• ⏱️ Real-time sync with Telegram\n"
            "• 📈 Track your productivity\n\n"
            "🔗 <b>Login here:</b>\n"
            "https://postiz.komror.com",
        )
