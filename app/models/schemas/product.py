from datetime import datetime

from pydantic import Field

from app.models.schemas.base import BaseSchema


class ProductResponse(BaseSchema):

    id: int = Field(..., description="Product ID")
    name: str = Field(..., description="Product name")
    description: str = Field(..., description="Product description")
    created_at: datetime = Field(..., description="Product created")
    updated_at: datetime = Field(..., description="Product updated")


class ProductCreate(BaseSchema):

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Product's name",
        examples=["Laptop", "Smartphone"],
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Product's description",
        examples=["A high-performance laptop", "Latest smartphone model"],
    )


class ProductUpdate(BaseSchema):

    name: str | None = Field(None, description="Product name")
    description: str | None = Field(None, description="Product description")


