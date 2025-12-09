"""Telegram webhook routes for memolog."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from telegram import Bot, Update

from app.common.response import ResponseBuilder, ResponseMessage
from app.services.telegram_service import TelegramService
from config.settings import get_settings

router = APIRouter(prefix="/telegram", tags=["Telegram"])


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
async def telegram_webhook(
    request: Request,
    service: TelegramService = Depends(),
):
    """Handle incoming Telegram webhook updates.

    This endpoint receives updates from Telegram's servers
    and processes them to respond to user messages.

    Args:
        request: FastAPI request object.
        service: Telegram service instance.

    Returns:
        Empty response (Telegram expects 200 OK).
    """
    settings = get_settings()

    if not settings.telegram_bot_token:
        raise HTTPException(
            status_code=500,
            detail="Telegram bot token not configured",
        )

    try:
        # Parse the update from Telegram
        data = await request.json()
        update = Update.de_json(data, Bot(token=settings.telegram_bot_token))

        if update.message and update.message.text:
            chat_id = update.message.chat_id
            text = update.message.text

            # Process the message
            response_text = await service.handle_message(text, chat_id)

            # Send response back to Telegram
            bot = Bot(token=settings.telegram_bot_token)
            await bot.send_message(
                chat_id=chat_id,
                text=response_text,
                parse_mode="HTML",
            )

        return {"ok": True}

    except Exception as e:
        # Log error but return 200 to Telegram to prevent retries
        import logging
        logging.error(f"Telegram webhook error: {e}")
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

    try:
        bot = Bot(token=settings.telegram_bot_token)
        webhook_url = f"{settings.telegram_webhook_url}/api/v1/telegram/webhook"

        await bot.set_webhook(url=webhook_url)

        webhook_info = await bot.get_webhook_info()

        return (
            ResponseBuilder[WebhookInfo]()
            .success()
            .add_data(
                WebhookInfo(
                    url=webhook_info.url,
                    has_custom_certificate=webhook_info.has_custom_certificate,
                    pending_update_count=webhook_info.pending_update_count,
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

    try:
        bot = Bot(token=settings.telegram_bot_token)
        await bot.delete_webhook()

        return (
            ResponseBuilder[None]()
            .success()
            .add_message("Webhook deleted successfully")
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

    try:
        bot = Bot(token=settings.telegram_bot_token)
        webhook_info = await bot.get_webhook_info()

        return (
            ResponseBuilder[WebhookInfo]()
            .success()
            .add_data(
                WebhookInfo(
                    url=webhook_info.url or "",
                    has_custom_certificate=webhook_info.has_custom_certificate,
                    pending_update_count=webhook_info.pending_update_count,
                )
            )
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
async def test_message(
    message: TelegramMessage,
    service: TelegramService = Depends(),
) -> ResponseMessage[str]:
    """Test message processing directly.

    Useful for testing bot responses without going through Telegram.

    Args:
        message: Test message with text.
        service: Telegram service instance.

    Returns:
        ResponseMessage with bot's response.
    """
    response = await service.handle_message(message.text, message.chat_id)

    return (
        ResponseBuilder[str]()
        .success()
        .add_data(response)
        .build()
    )
