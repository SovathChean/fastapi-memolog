"""Health check schemas."""

from app.models.schemas.base import BaseSchema


class HealthResponse(BaseSchema):
    """Response model for health check endpoint."""

    status: str
    message: str = "Service is running"
