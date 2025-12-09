"""User feature schemas."""

from datetime import datetime

from pydantic import Field

from app.models.schemas.base import BaseSchema


class UserResponse(BaseSchema):
    """Response model for user endpoints."""

    id: int = Field(..., description="User ID")
    name: str = Field(..., description="User's name")
    email: str = Field(..., description="User's email address")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class UserCreate(BaseSchema):
    """Request model for creating a user."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User's name",
        examples=["John Doe", "Alice Smith"],
    )
    email: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="User's email address",
        examples=["john@example.com", "alice@example.com"],
    )


class UserUpdate(BaseSchema):
    """Request model for updating a user."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="User's name",
        examples=["John Doe", "Alice Smith"],
    )
    email: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="User's email address",
        examples=["john@example.com", "alice@example.com"],
    )
