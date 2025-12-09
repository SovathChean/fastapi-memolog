"""Unified response builder and schemas for consistent API responses."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Generic, Self, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.common.constants import ErrorCodes
from app.common.exceptions import NotFoundError, ValidationError

T = TypeVar("T")


class ResponseStatus(BaseModel):
    """Status information for API responses."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "code": 0,
                "errorMessage": None,
                "errorCode": None,
                "warning": None,
                "message": None,
            }
        },
    )

    code: int = Field(
        default=0,
        description="Status code: 0 = success, 1 = failure",
    )
    error_message: str | None = Field(
        default=None,
        alias="errorMessage",
        description="Human-readable error message",
    )
    error_code: int | None = Field(
        default=None,
        alias="errorCode",
        description="Application-specific error code",
    )
    warning: str | None = Field(
        default=None,
        description="Optional warning message",
    )
    message: str | None = Field(
        default=None,
        description="Optional success/info message",
    )


class ResponseMessage(BaseModel, Generic[T]):
    """Generic API response wrapper."""

    model_config = ConfigDict(
        populate_by_name=True,
    )

    status: ResponseStatus = Field(
        default_factory=ResponseStatus,
        description="Response status information",
    )
    data: T | None = Field(
        default=None,
        description="Response payload",
    )


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    model_config = ConfigDict(populate_by_name=True)

    page: int = Field(default=1, description="Current page number")
    page_size: int = Field(
        default=10,
        alias="pageSize",
        description="Items per page",
    )
    total_items: int = Field(
        default=0,
        alias="totalItems",
        description="Total number of items",
    )
    total_pages: int = Field(
        default=0,
        alias="totalPages",
        description="Total number of pages",
    )


class PaginatedResponse(ResponseMessage[list[T]], Generic[T]):
    """Paginated API response wrapper."""

    pagination: PaginationMeta = Field(
        default_factory=PaginationMeta,
        description="Pagination metadata",
    )


class ResponseBuilder(Generic[T]):
    """Builder pattern for constructing API responses.

    Provides fluent interface for building consistent API responses
    with proper status codes, error handling, and pagination.

    Example:
        # Success response
        response = (
            ResponseBuilder[HelloResponse]()
            .success()
            .add_data(HelloResponse(message="Hello", name="World"))
            .build()
        )

        # Error response
        response = (
            ResponseBuilder[None]()
            .fail()
            .add_error_code(1001)
            .add_error_message("Name cannot be empty")
            .build()
        )

        # Paginated response
        response = (
            ResponseBuilder[list[Item]]()
            .success()
            .add_data(items)
            .add_page(total_pages=5, page=1, page_size=10, total_items=50)
            .build_paginated()
        )
    """

    def __init__(self) -> None:
        """Initialize builder with default values."""
        self._status = ResponseStatus()
        self._data: T | None = None
        self._pagination: PaginationMeta | None = None

    def success(self) -> Self:
        """Mark response as successful (code=0).

        Returns:
            Self for method chaining.
        """
        self._status.code = 0
        return self

    def fail(self) -> Self:
        """Mark response as failed (code=1).

        Returns:
            Self for method chaining.
        """
        self._status.code = 1
        return self

    def add_data(self, data: T) -> Self:
        """Add response data payload.

        Args:
            data: The data to include in the response.

        Returns:
            Self for method chaining.
        """
        self._data = data
        return self

    def add_error_code(self, error_code: int) -> Self:
        """Add application-specific error code.

        Args:
            error_code: The error code to include.

        Returns:
            Self for method chaining.
        """
        self._status.error_code = error_code
        return self

    def add_error_message(self, error_message: str) -> Self:
        """Add human-readable error message.

        Args:
            error_message: The error message to include.

        Returns:
            Self for method chaining.
        """
        self._status.error_message = error_message
        return self

    def add_error_code_and_message(
        self,
        error_code: int,
        error_message: str,
    ) -> Self:
        """Add both error code and message.

        Args:
            error_code: The error code to include.
            error_message: The error message to include.

        Returns:
            Self for method chaining.
        """
        self._status.error_code = error_code
        self._status.error_message = error_message
        return self

    def add_warning(self, warning: str) -> Self:
        """Add warning message.

        Args:
            warning: The warning message to include.

        Returns:
            Self for method chaining.
        """
        self._status.warning = warning
        return self

    def add_message(self, message: str) -> Self:
        """Add informational message.

        Args:
            message: The message to include.

        Returns:
            Self for method chaining.
        """
        self._status.message = message
        return self

    def add_page(
        self,
        total_pages: int,
        page: int = 1,
        page_size: int = 10,
        total_items: int = 0,
    ) -> Self:
        """Add pagination metadata.

        Args:
            total_pages: Total number of pages.
            page: Current page number.
            page_size: Number of items per page.
            total_items: Total number of items.

        Returns:
            Self for method chaining.
        """
        self._pagination = PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        )
        return self

    def build(self) -> ResponseMessage[T]:
        """Build the response message.

        Returns:
            ResponseMessage with configured status and data.
        """
        return ResponseMessage[T](
            status=self._status,
            data=self._data,
        )

    def build_paginated(self) -> PaginatedResponse[Any]:
        """Build a paginated response message.

        Returns:
            PaginatedResponse with configured status, data, and pagination.

        Raises:
            ValueError: If pagination metadata was not set.
        """
        if self._pagination is None:
            raise ValueError(
                "Pagination metadata not set. Call add_page() before build_paginated()."
            )
        return PaginatedResponse(
            status=self._status,
            data=self._data,  # type: ignore[arg-type]
            pagination=self._pagination,
        )


def success_response(data: T, message: str | None = None) -> ResponseMessage[T]:
    """Create a success response with data.

    Args:
        data: Response data payload.
        message: Optional success message.

    Returns:
        ResponseMessage with success status.
    """
    builder = ResponseBuilder[T]().success().add_data(data)
    if message:
        builder.add_message(message)
    return builder.build()


def error_response(
    error_code: int,
    error_message: str,
) -> ResponseMessage[None]:
    """Create an error response.

    Args:
        error_code: Application-specific error code.
        error_message: Human-readable error message.

    Returns:
        ResponseMessage with failure status.
    """
    return (
        ResponseBuilder[None]()
        .fail()
        .add_error_code(error_code)
        .add_error_message(error_message)
        .build()
    )


async def handle_request(
    action: Callable[[], Awaitable[Any]],
    response_model: type | None = None,
    success_message: str | None = None,
) -> ResponseMessage[Any]:
    """Execute async action with automatic error handling.

    Wraps service calls with try/catch and returns consistent ResponseMessage.

    Args:
        action: Async callable that returns the data (use lambda for parameters).
        response_model: Pydantic model to validate response (uses model_validate).
        success_message: Optional success message to include.

    Returns:
        ResponseMessage with success data or error.

    Example:
        return await handle_request(
            action=lambda: self.service.create_user(data),
            response_model=UserResponse,
            success_message="User created successfully",
        )
    """
    try:
        result = await action()

        # Convert to response model if provided
        data = response_model.model_validate(result) if response_model else result

        builder = ResponseBuilder[Any]().success().add_data(data)
        if success_message:
            builder.add_message(success_message)
        return builder.build()

    except ValidationError as e:
        return (
            ResponseBuilder[Any]()
            .fail()
            .add_error_code(ErrorCodes.VALIDATION_ERROR)
            .add_error_message(str(e))
            .build()
        )
    except NotFoundError as e:
        return (
            ResponseBuilder[Any]()
            .fail()
            .add_error_code(ErrorCodes.NOT_FOUND)
            .add_error_message(str(e))
            .build()
        )
    except Exception as e:
        return (
            ResponseBuilder[Any]()
            .fail()
            .add_error_code(ErrorCodes.INTERNAL_ERROR)
            .add_error_message(str(e))
            .build()
        )
