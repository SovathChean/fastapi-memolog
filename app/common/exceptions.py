"""Custom exceptions and exception handlers."""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Base application exception."""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(AppException):
    """Resource not found."""

    def __init__(self, resource: str, identifier: str | int):
        super().__init__(
            f"{resource} with identifier '{identifier}' not found",
            "NOT_FOUND",
        )


class ValidationError(AppException):
    """Validation error."""

    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR")


class DatabaseError(AppException):
    """Database operation error."""

    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message, "DATABASE_ERROR")


class UnauthorizedError(AppException):
    """Unauthorized access error."""

    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, "UNAUTHORIZED")


class ForbiddenError(AppException):
    """Forbidden access error."""

    def __init__(self, message: str = "Access forbidden"):
        super().__init__(message, "FORBIDDEN")


def to_http_exception(exc: AppException) -> HTTPException:
    """Convert AppException to HTTPException."""
    status_map = {
        "NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "VALIDATION_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "DATABASE_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "UNAUTHORIZED": status.HTTP_401_UNAUTHORIZED,
        "FORBIDDEN": status.HTTP_403_FORBIDDEN,
        "INTERNAL_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    }
    return HTTPException(
        status_code=status_map.get(exc.code, status.HTTP_500_INTERNAL_SERVER_ERROR),
        detail={"message": exc.message, "code": exc.code},
    )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle AppException and return JSON response."""
    status_map = {
        "NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "VALIDATION_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "DATABASE_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "UNAUTHORIZED": status.HTTP_401_UNAUTHORIZED,
        "FORBIDDEN": status.HTTP_403_FORBIDDEN,
        "INTERNAL_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    }
    return JSONResponse(
        status_code=status_map.get(exc.code, status.HTTP_500_INTERNAL_SERVER_ERROR),
        content={"message": exc.message, "code": exc.code},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register exception handlers with the FastAPI app."""
    app.add_exception_handler(AppException, app_exception_handler)
