"""Error handler middleware for Telegram bot."""

import logging

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle errors in the Telegram bot.

    This middleware catches all unhandled exceptions and logs them,
    then sends a user-friendly error message to the chat.

    Args:
        update: Telegram update object (may be None).
        context: Callback context with error information.
    """
    logger.error(f"Exception while handling an update: {context.error}")

    # Log the traceback
    if context.error:
        import traceback
        tb_list = traceback.format_exception(
            type(context.error),
            context.error,
            context.error.__traceback__,
        )
        tb_string = "".join(tb_list)
        logger.error(f"Traceback:\n{tb_string}")

    # Try to send error message to user
    if isinstance(update, Update) and update.effective_chat:
        error_message = (
            "❌ Sorry, something went wrong while processing your request.\n\n"
            "Please try again or use /help to see available commands."
        )

        try:
            await update.effective_chat.send_message(
                text=error_message,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Failed to send error message to user: {e}")
