"""Crypto bot singleton class for P&L tracking."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from config.settings import get_settings

if TYPE_CHECKING:
    from app.crypto_bot.handlers.base import BaseCryptoHandler


class CryptoBot:
    """Singleton Crypto bot for P&L tracking.

    This class manages the lifecycle of the Crypto Telegram bot,
    separate from the main memolog task bot.
    """

    _instance: CryptoBot | None = None
    _initialized: bool = False

    def __new__(cls) -> CryptoBot:
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize bot attributes (only runs once due to singleton)."""
        if hasattr(self, "_init_done"):
            return
        self._init_done = True
        self.logger = logging.getLogger(self.__class__.__name__)
        self.application: Application | None = None
        self._handlers: list[BaseCryptoHandler] = []

    async def initialize(self) -> None:
        """Initialize the bot with Application builder."""
        if self._initialized:
            self.logger.info("CryptoBot already initialized")
            return

        settings = get_settings()

        if not settings.crypto_bot_token:
            self.logger.warning(
                "Crypto bot token not configured, skipping initialization"
            )
            return

        self.logger.info("Initializing CryptoBot...")

        # Build the application
        self.application = (
            Application.builder().token(settings.crypto_bot_token).build()
        )

        # Register handlers
        await self._register_handlers()

        # Initialize the application
        await self.application.initialize()

        self._initialized = True
        self.logger.info("CryptoBot initialized successfully")

    async def _register_handlers(self) -> None:
        """Register all command and message handlers."""
        if not self.application:
            return

        from app.crypto_bot.handlers import StartHandler, TradeHandler

        # Create handler instances
        self._handlers = [
            StartHandler(),
            TradeHandler(),
        ]

        # Register command handlers
        for handler in self._handlers:
            for command in handler.commands:
                self.application.add_handler(CommandHandler(command, handler.handle))
                self.logger.debug(f"Registered crypto command: /{command}")

        # Register message handler for natural text (trade input)
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self._handle_natural_text,
            )
        )

        self.logger.info(f"Registered {len(self._handlers)} crypto handlers")

    async def _handle_natural_text(
        self,
        update: Update,
        context,
    ) -> None:
        """Handle natural language text messages.

        Detects trade input format and processes accordingly.
        """
        if not update.message or not update.message.text:
            return

        text = update.message.text.strip()

        # Check if it looks like trade input (contains "add:" or key-value pairs)
        text_lower = text.lower()
        if text_lower.startswith("add:") or (
            "coin:" in text_lower and "entry" in text_lower
        ):
            from app.crypto_bot.handlers import TradeHandler

            handler = TradeHandler()
            await handler.handle_add_natural(update, context, text)
            return

        # Check if it looks like close input
        if text_lower.startswith("close"):
            from app.crypto_bot.handlers import TradeHandler

            handler = TradeHandler()
            await handler.handle_close_natural(update, context, text)
            return

        # Default: show help
        await update.message.reply_text(
            "💰 <b>Crypto P&L Bot</b>\n\n"
            "Commands:\n"
            "/add - Add a new trade\n"
            "/trades - View recent trades\n"
            "/pnl - View P&L summary\n"
            "/open - View open trades\n\n"
            "Or paste trade details:\n"
            "<code>Add:\n"
            "coin: BTCUSDT\n"
            "Budget: 100$\n"
            "Entry: 42000\n"
            "stoploss: 41000</code>",
            parse_mode="HTML",
        )

    async def process_update(self, update_data: dict) -> None:
        """Process an incoming webhook update."""
        if not self.application or not self._initialized:
            self.logger.error("CryptoBot not initialized, cannot process update")
            return

        try:
            update = Update.de_json(update_data, self.application.bot)
            await self.application.process_update(update)
        except Exception as e:
            self.logger.error(f"Error processing crypto update: {e}")
            raise

    async def set_webhook(self, url: str) -> bool:
        """Set the webhook URL for receiving updates."""
        if not self.application or not self._initialized:
            self.logger.error("CryptoBot not initialized, cannot set webhook")
            return False

        try:
            await self.application.bot.set_webhook(url=url)
            self.logger.info(f"Crypto webhook set to: {url}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to set crypto webhook: {e}")
            return False

    async def delete_webhook(self) -> bool:
        """Delete the current webhook."""
        if not self.application or not self._initialized:
            return False

        try:
            await self.application.bot.delete_webhook()
            self.logger.info("Crypto webhook deleted")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete crypto webhook: {e}")
            return False

    async def get_webhook_info(self) -> dict | None:
        """Get current webhook information."""
        if not self.application or not self._initialized:
            return None

        try:
            info = await self.application.bot.get_webhook_info()
            return {
                "url": info.url,
                "has_custom_certificate": info.has_custom_certificate,
                "pending_update_count": info.pending_update_count,
            }
        except Exception as e:
            self.logger.error(f"Failed to get crypto webhook info: {e}")
            return None

    @property
    def is_initialized(self) -> bool:
        """Check if bot is initialized."""
        return self._initialized
