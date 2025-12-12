"""Telegram user schemas for API requests and responses."""

from datetime import datetime

from pydantic import Field

from app.models.schemas.base import BaseSchema


class TelegramUserCreate(BaseSchema):
    """Schema for creating/updating a Telegram user."""

    telegram_id: int = Field(..., description="Unique Telegram user ID")
    chat_id: int | None = Field(None, description="Chat ID for messaging")
    username: str | None = Field(None, max_length=255, description="@username")
    first_name: str = Field(..., max_length=255, description="User's first name")
    last_name: str | None = Field(None, max_length=255, description="User's last name")
    language_code: str | None = Field(None, max_length=10, description="Language code")


class TelegramUserResponse(BaseSchema):
    """Schema for Telegram user response."""

    id: int = Field(..., description="Internal user ID")
    telegram_id: int = Field(..., description="Telegram user ID")
    chat_id: int | None = Field(None, description="Chat ID")
    username: str | None = Field(None, description="@username")
    first_name: str = Field(..., description="First name")
    last_name: str | None = Field(None, description="Last name")
    language_code: str | None = Field(None, description="Language code")
    is_active: bool = Field(..., description="Is user active")
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")
