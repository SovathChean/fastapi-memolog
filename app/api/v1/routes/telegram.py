"""Telegram webhook routes for memolog."""

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.common.response import ResponseBuilder, ResponseMessage
from app.telegram_bot import TelegramBot
from config.settings import get_settings

router = APIRouter(prefix="/telegram", tags=["Telegram"])
logger = logging.getLogger(__name__)


class TelegramMessage(BaseModel):
    """Telegram message model for direct API testing."""

    text: str = Field(..., description="Message text")
    chat_id: int = Field(default=0, description="Chat ID (optional for testing)")


class WebhookInfo(BaseModel):
    """Webhook configuration info."""

    url: str = Field(..., description="Webhook URL")
    has_custom_certificate: bool = False
    pending_update_count: int = 0


@router.post(
    "/webhook",
    summary="Telegram webhook endpoint",
    description="Receives updates from Telegram Bot API",
    include_in_schema=False,  # Hide from OpenAPI as it's for Telegram
)
async def telegram_webhook(request: Request):
    """Handle incoming Telegram webhook updates.

    This endpoint receives updates from Telegram's servers
    and processes them using the handler-based architecture.

    Args:
        request: FastAPI request object.

    Returns:
        Empty response (Telegram expects 200 OK).
    """
    settings = get_settings()

    if not settings.telegram_bot_token:
        raise HTTPException(
            status_code=500,
            detail="Telegram bot token not configured",
        )

    bot = TelegramBot()

    if not bot.is_initialized:
        raise HTTPException(
            status_code=500,
            detail="Telegram bot not initialized",
        )

    try:
        data = await request.json()
        await bot.process_update(data)
        return {"ok": True}

    except Exception as e:
        logger.error(f"Telegram webhook error: {e}")
        return {"ok": False, "error": str(e)}


@router.post(
    "/set-webhook",
    response_model=ResponseMessage[WebhookInfo],
    summary="Set Telegram webhook URL",
    description="Configure the webhook URL for Telegram bot",
)
async def set_webhook():
    """Set the Telegram webhook URL.

    Configures Telegram to send updates to this server's webhook endpoint.

    Returns:
        ResponseMessage with webhook configuration info.
    """
    settings = get_settings()

    if not settings.telegram_bot_token:
        return (
            ResponseBuilder[WebhookInfo]()
            .fail()
            .add_error_message("Telegram bot token not configured")
            .build()
        )

    if not settings.telegram_webhook_url:
        return (
            ResponseBuilder[WebhookInfo]()
            .fail()
            .add_error_message("Telegram webhook URL not configured")
            .build()
        )

    bot = TelegramBot()

    if not bot.is_initialized:
        return (
            ResponseBuilder[WebhookInfo]()
            .fail()
            .add_error_message("Telegram bot not initialized")
            .build()
        )

    try:
        webhook_url = f"{settings.telegram_webhook_url}/api/v1/telegram/webhook"
        success = await bot.set_webhook(webhook_url)

        if not success:
            return (
                ResponseBuilder[WebhookInfo]()
                .fail()
                .add_error_message("Failed to set webhook")
                .build()
            )

        info = await bot.get_webhook_info()

        return (
            ResponseBuilder[WebhookInfo]()
            .success()
            .add_data(
                WebhookInfo(
                    url=info["url"] if info else "",
                    has_custom_certificate=(
                        info["has_custom_certificate"] if info else False
                    ),
                    pending_update_count=info["pending_update_count"] if info else 0,
                )
            )
            .add_message("Webhook set successfully")
            .build()
        )

    except Exception as e:
        return (
            ResponseBuilder[WebhookInfo]()
            .fail()
            .add_error_message(f"Failed to set webhook: {e}")
            .build()
        )


@router.delete(
    "/webhook",
    response_model=ResponseMessage[None],
    summary="Delete Telegram webhook",
    description="Remove the webhook configuration from Telegram",
)
async def delete_webhook():
    """Delete the Telegram webhook.

    Removes the webhook configuration so the bot stops receiving updates.

    Returns:
        ResponseMessage with success or error.
    """
    settings = get_settings()

    if not settings.telegram_bot_token:
        return (
            ResponseBuilder[None]()
            .fail()
            .add_error_message("Telegram bot token not configured")
            .build()
        )

    bot = TelegramBot()

    if not bot.is_initialized:
        return (
            ResponseBuilder[None]()
            .fail()
            .add_error_message("Telegram bot not initialized")
            .build()
        )

    try:
        success = await bot.delete_webhook()

        if success:
            return (
                ResponseBuilder[None]()
                .success()
                .add_message("Webhook deleted successfully")
                .build()
            )
        else:
            return (
                ResponseBuilder[None]()
                .fail()
                .add_error_message("Failed to delete webhook")
                .build()
            )

    except Exception as e:
        return (
            ResponseBuilder[None]()
            .fail()
            .add_error_message(f"Failed to delete webhook: {e}")
            .build()
        )


@router.get(
    "/webhook",
    response_model=ResponseMessage[WebhookInfo],
    summary="Get Telegram webhook info",
    description="Get current webhook configuration from Telegram",
)
async def get_webhook_info():
    """Get current Telegram webhook information.

    Returns:
        ResponseMessage with current webhook configuration.
    """
    settings = get_settings()

    if not settings.telegram_bot_token:
        return (
            ResponseBuilder[WebhookInfo]()
            .fail()
            .add_error_message("Telegram bot token not configured")
            .build()
        )

    bot = TelegramBot()

    if not bot.is_initialized:
        return (
            ResponseBuilder[WebhookInfo]()
            .fail()
            .add_error_message("Telegram bot not initialized")
            .build()
        )

    try:
        info = await bot.get_webhook_info()

        if info:
            return (
                ResponseBuilder[WebhookInfo]()
                .success()
                .add_data(
                    WebhookInfo(
                        url=info["url"],
                        has_custom_certificate=info["has_custom_certificate"],
                        pending_update_count=info["pending_update_count"],
                    )
                )
                .build()
            )
        else:
            return (
                ResponseBuilder[WebhookInfo]()
                .fail()
                .add_error_message("Failed to get webhook info")
                .build()
            )

    except Exception as e:
        return (
            ResponseBuilder[WebhookInfo]()
            .fail()
            .add_error_message(f"Failed to get webhook info: {e}")
            .build()
        )


@router.post(
    "/test",
    response_model=ResponseMessage[str],
    summary="Test message processing",
    description="Test the bot's message processing without Telegram",
)
async def test_message(message: TelegramMessage) -> ResponseMessage[str]:
    """Test message processing directly.

    Useful for testing bot responses without going through Telegram.
    Note: This is a simplified test endpoint. For full testing,
    use the actual webhook with a test update payload.

    Args:
        message: Test message with text.

    Returns:
        ResponseMessage with acknowledgment.
    """
    bot = TelegramBot()

    if not bot.is_initialized:
        return (
            ResponseBuilder[str]()
            .fail()
            .add_error_message("Telegram bot not initialized")
            .build()
        )

    # Create a mock update payload for testing
    test_update = {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "date": 1234567890,
            "chat": {"id": message.chat_id, "type": "private"},
            "text": message.text,
        },
    }

    try:
        await bot.process_update(test_update)
        return (
            ResponseBuilder[str]()
            .success()
            .add_data(f"Processed message: {message.text}")
            .build()
        )
    except Exception as e:
        return (
            ResponseBuilder[str]()
            .fail()
            .add_error_message(f"Error processing message: {e}")
            .build()
        )
