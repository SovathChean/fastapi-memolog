"""Crypto bot webhook routes."""

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.common.response import ResponseBuilder, ResponseMessage
from app.crypto_bot import CryptoBot
from config.settings import get_settings

router = APIRouter(prefix="/crypto", tags=["Crypto Bot"])
logger = logging.getLogger(__name__)


class WebhookInfo(BaseModel):
    """Webhook configuration info."""

    url: str = Field(..., description="Webhook URL")
    has_custom_certificate: bool = False
    pending_update_count: int = 0


@router.post(
    "/webhook",
    summary="Crypto bot webhook endpoint",
    description="Receives updates from Telegram Bot API for crypto bot",
    include_in_schema=False,
)
async def crypto_webhook(request: Request):
    """Handle incoming Crypto bot webhook updates."""
    settings = get_settings()

    if not settings.crypto_bot_token:
        raise HTTPException(
            status_code=500,
            detail="Crypto bot token not configured",
        )

    bot = CryptoBot()

    if not bot.is_initialized:
        raise HTTPException(
            status_code=500,
            detail="Crypto bot not initialized",
        )

    try:
        data = await request.json()
        await bot.process_update(data)
        return {"ok": True}

    except Exception as e:
        logger.error(f"Crypto webhook error: {e}")
        return {"ok": False, "error": str(e)}


@router.post(
    "/set-webhook",
    response_model=ResponseMessage[WebhookInfo],
    summary="Set Crypto bot webhook URL",
    description="Configure the webhook URL for Crypto bot",
)
async def set_crypto_webhook():
    """Set the Crypto bot webhook URL."""
    settings = get_settings()

    if not settings.crypto_bot_token:
        return (
            ResponseBuilder[WebhookInfo]()
            .fail()
            .add_error_message("Crypto bot token not configured")
            .build()
        )

    if not settings.crypto_webhook_url:
        return (
            ResponseBuilder[WebhookInfo]()
            .fail()
            .add_error_message("Crypto webhook URL not configured")
            .build()
        )

    bot = CryptoBot()

    if not bot.is_initialized:
        return (
            ResponseBuilder[WebhookInfo]()
            .fail()
            .add_error_message("Crypto bot not initialized")
            .build()
        )

    try:
        webhook_url = f"{settings.crypto_webhook_url}/api/v1/crypto/webhook"
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
            .add_message("Crypto webhook set successfully")
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
    summary="Delete Crypto bot webhook",
    description="Remove the webhook configuration from Crypto bot",
)
async def delete_crypto_webhook():
    """Delete the Crypto bot webhook."""
    settings = get_settings()

    if not settings.crypto_bot_token:
        return (
            ResponseBuilder[None]()
            .fail()
            .add_error_message("Crypto bot token not configured")
            .build()
        )

    bot = CryptoBot()

    if not bot.is_initialized:
        return (
            ResponseBuilder[None]()
            .fail()
            .add_error_message("Crypto bot not initialized")
            .build()
        )

    try:
        success = await bot.delete_webhook()

        if success:
            return (
                ResponseBuilder[None]()
                .success()
                .add_message("Crypto webhook deleted successfully")
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
    summary="Get Crypto bot webhook info",
    description="Get current webhook configuration from Crypto bot",
)
async def get_crypto_webhook_info():
    """Get current Crypto bot webhook information."""
    settings = get_settings()

    if not settings.crypto_bot_token:
        return (
            ResponseBuilder[WebhookInfo]()
            .fail()
            .add_error_message("Crypto bot token not configured")
            .build()
        )

    bot = CryptoBot()

    if not bot.is_initialized:
        return (
            ResponseBuilder[WebhookInfo]()
            .fail()
            .add_error_message("Crypto bot not initialized")
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
