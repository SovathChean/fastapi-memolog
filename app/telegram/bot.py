"""Telegram bot singleton class with handler-based architecture."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from config.settings import get_settings

if TYPE_CHECKING:
    from app.telegram.handlers.base import BaseHandler


class TelegramBot:
    """Singleton Telegram bot with handler registration.

    This class manages the lifecycle of the Telegram bot application,
    including handler registration, webhook management, and message processing.
    """

    _instance: TelegramBot | None = None
    _initialized: bool = False

    def __new__(cls) -> TelegramBot:
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
        self._handlers: list[BaseHandler] = []
        self._message_handler: BaseHandler | None = None

    async def initialize(self) -> None:
        """Initialize the bot with Application builder.

        This sets up the telegram bot application and registers all handlers.
        Should be called during application startup.
        """
        if self._initialized:
            self.logger.info("TelegramBot already initialized")
            return

        settings = get_settings()

        if not settings.telegram_bot_token:
            self.logger.warning(
                "Telegram bot token not configured, skipping initialization"
            )
            return

        self.logger.info("Initializing TelegramBot...")

        # Build the application
        self.application = (
            Application.builder()
            .token(settings.telegram_bot_token)
            .build()
        )

        # Register handlers
        await self._register_handlers()

        # Initialize the application
        await self.application.initialize()

        self._initialized = True
        self.logger.info("TelegramBot initialized successfully")

    async def _register_handlers(self) -> None:
        """Register all command and message handlers."""
        if not self.application:
            return

        # Import handlers here to avoid circular imports
        from app.telegram.handlers import (
            ListHandler,
            ReportHandler,
            SearchHandler,
            StartHandler,
            TaskHandler,
        )
        from app.telegram.middleware import error_handler

        # Create handler instances
        self._handlers = [
            StartHandler(),
            TaskHandler(),
            ListHandler(),
            SearchHandler(),
            ReportHandler(),
        ]

        # Register command handlers
        for handler in self._handlers:
            for command in handler.commands:
                self.application.add_handler(
                    CommandHandler(command, handler.handle)
                )
                self.logger.debug(f"Registered command: /{command}")

        # Register message handler for natural language
        # Use the SearchHandler for natural text processing
        self._message_handler = SearchHandler()
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self._handle_natural_text,
            )
        )

        # Register error handler
        self.application.add_error_handler(error_handler)

        self.logger.info(f"Registered {len(self._handlers)} handlers")

    async def _handle_natural_text(
        self,
        update: Update,
        context,
    ) -> None:
        """Handle natural language text messages.

        Delegates to appropriate handler based on intent detection.

        Args:
            update: Telegram update object.
            context: Callback context.
        """
        if not update.message or not update.message.text:
            return

        text = update.message.text.lower()

        # Simple intent detection
        from app.telegram.handlers import (
            ListHandler,
            ReportHandler,
            SearchHandler,
            TaskHandler,
        )

        # Check for add intent
        if any(word in text for word in ["add", "create", "new task"]):
            handler = TaskHandler()
            await handler.handle_add_natural(update, context)
            return

        # Check for list intent
        if any(word in text for word in ["today", "daily", "today's"]):
            handler = ListHandler()
            await handler.handle_period(update, context, "daily")
            return

        if any(word in text for word in ["week", "weekly", "this week"]):
            handler = ListHandler()
            await handler.handle_period(update, context, "weekly")
            return

        if any(word in text for word in ["month", "monthly", "this month"]):
            handler = ListHandler()
            await handler.handle_period(update, context, "monthly")
            return

        # Check for report intent
        if any(word in text for word in ["report", "summary", "progress", "status"]):
            handler = ReportHandler()
            period = "daily"
            if "week" in text:
                period = "weekly"
            elif "month" in text:
                period = "monthly"
            await handler.handle_report(update, context, period)
            return

        # Default: treat as search
        handler = SearchHandler()
        await handler.handle_search(update, context, text)

    async def process_update(self, update_data: dict) -> None:
        """Process an incoming webhook update.

        Args:
            update_data: Raw update data from Telegram webhook.
        """
        if not self.application or not self._initialized:
            self.logger.error("Bot not initialized, cannot process update")
            return

        try:
            update = Update.de_json(update_data, self.application.bot)
            await self.application.process_update(update)
        except Exception as e:
            self.logger.error(f"Error processing update: {e}")
            raise

    async def set_webhook(self, url: str) -> bool:
        """Set the webhook URL for receiving updates.

        Args:
            url: Full webhook URL.

        Returns:
            True if webhook was set successfully.
        """
        if not self.application or not self._initialized:
            self.logger.error("Bot not initialized, cannot set webhook")
            return False

        try:
            await self.application.bot.set_webhook(url=url)
            self.logger.info(f"Webhook set to: {url}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to set webhook: {e}")
            return False

    async def delete_webhook(self) -> bool:
        """Delete the current webhook.

        Returns:
            True if webhook was deleted successfully.
        """
        if not self.application or not self._initialized:
            return False

        try:
            await self.application.bot.delete_webhook()
            self.logger.info("Webhook deleted")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete webhook: {e}")
            return False

    async def get_webhook_info(self) -> dict | None:
        """Get current webhook information.

        Returns:
            Webhook info dict or None if failed.
        """
        if not self.application or not self._initialized:
            return None

        try:
            info = await self.application.bot.get_webhook_info()
            return {
                "url": info.url or "",
                "has_custom_certificate": info.has_custom_certificate,
                "pending_update_count": info.pending_update_count,
            }
        except Exception as e:
            self.logger.error(f"Failed to get webhook info: {e}")
            return None

    async def start_polling(self) -> None:
        """Start polling mode for development.

        This is useful for local development without a webhook.
        """
        if not self.application or not self._initialized:
            self.logger.error("Bot not initialized, cannot start polling")
            return

        self.logger.info("Starting polling mode...")
        await self.application.start()
        await self.application.updater.start_polling()

    async def stop_polling(self) -> None:
        """Stop polling mode."""
        if not self.application or not self._initialized:
            return

        if self.application.updater and self.application.updater.running:
            await self.application.updater.stop()
            await self.application.stop()
            self.logger.info("Polling stopped")

    async def shutdown(self) -> None:
        """Cleanup resources on shutdown.

        Should be called during application shutdown.
        """
        if not self._initialized:
            return

        self.logger.info("Shutting down TelegramBot...")

        try:
            await self.stop_polling()

            if self.application:
                await self.application.shutdown()

            self._initialized = False
            self.logger.info("TelegramBot shutdown complete")
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")

    @property
    def is_initialized(self) -> bool:
        """Check if the bot is initialized."""
        return self._initialized

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (for testing)."""
        cls._instance = None
        cls._initialized = False


# Convenience function to get bot instance
def get_bot() -> TelegramBot:
    """Get the TelegramBot singleton instance.

    Returns:
        TelegramBot instance.
    """
    return TelegramBot()
