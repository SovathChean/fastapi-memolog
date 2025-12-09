"""Base schema classes."""

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        populate_by_name=True,
    )


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""

    model_config = ConfigDict(from_attributes=True)

    # These will be populated from ORM models
    # created_at: datetime | None = None
    # updated_at: datetime | None = None
