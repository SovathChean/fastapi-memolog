"""Start handler for crypto bot."""

from telegram import Update
from telegram.ext import ContextTypes

from app.crypto_bot.handlers.base import BaseCryptoHandler
from config.database import get_session_factory


class StartHandler(BaseCryptoHandler):
    """Handler for /start and /help commands."""

    @property
    def commands(self) -> list[str]:
        """Commands this handler responds to."""
        return ["start", "help"]

    async def handle(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /start and /help commands."""
        command = self.get_command_name(update)

        session_factory = get_session_factory()
        async with session_factory() as session:
            user = await self.get_or_create_user(update, session)

        if command == "start":
            await self._handle_start(update, user.first_name)
        else:
            await self._handle_help(update)

    async def _handle_start(self, update: Update, name: str) -> None:
        """Handle /start command."""
        welcome = (
            f"👋 Welcome {name}!\n\n"
            "💰 <b>Crypto P&L Tracker</b>\n\n"
            "I help you track your crypto trades and calculate P&L.\n\n"
            "<b>Commands:</b>\n"
            "/add - Add a new trade\n"
            "/trades - View recent trades\n"
            "/pnl - View P&L summary\n"
            "/open - View open trades\n"
            "/close [id] - Close a trade\n\n"
            "<b>Quick Add:</b>\n"
            "Just paste your trade details:\n"
            "<code>Add:\n"
            "coin: BTCUSDT\n"
            "Budget: 100$\n"
            "Entry: 42000\n"
            "stoploss: 41000\n"
            "Status: open</code>"
        )
        await self.send_message(update, welcome)

    async def _handle_help(self, update: Update) -> None:
        """Handle /help command."""
        help_text = (
            "💰 <b>Crypto P&L Bot - Help</b>\n\n"
            "<b>📝 Recording Trades</b>\n"
            "/add - Add a new trade interactively\n"
            "Or paste trade details directly\n\n"
            "<b>📊 Viewing Trades</b>\n"
            "/trades - View all recent trades\n"
            "/open - View open positions only\n"
            "/pnl - View profit/loss summary\n\n"
            "<b>✏️ Managing Trades</b>\n"
            "/close [id] [price] - Close a trade\n"
            "/delete [id] - Delete a trade\n\n"
            "<b>📋 Trade Format</b>\n"
            "<code>Add:\n"
            "coin: BTCUSDT\n"
            "Budget: 100$\n"
            "Entry: 42000\n"
            "stoploss: 41000\n"
            "take_profit: 45000\n"
            "leverage: 50\n"
            "Status: open\n"
            "reason: BTC breakout pattern</code>"
        )
        await self.send_message(update, help_text)
