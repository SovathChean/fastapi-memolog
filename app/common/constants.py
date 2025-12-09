"""Application constants."""

# API versioning
API_V1_PREFIX = "/api/v1"
API_V2_PREFIX = "/api/v2"

# Pagination defaults
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# CORS settings
CORS_ALLOW_ORIGINS = ["*"]
CORS_ALLOW_METHODS = ["*"]
CORS_ALLOW_HEADERS = ["*"]
CORS_ALLOW_CREDENTIALS = True


class StatusCodes:
    """Response status codes."""

    SUCCESS = 0
    FAILURE = 1


class ErrorCodes:
    """Application error codes."""

    # Validation errors (1000-1099)
    VALIDATION_ERROR = 1000
    INVALID_NAME = 1001
    INVALID_FORMAT = 1002
    REQUIRED_FIELD = 1003

    # Authentication errors (2000-2099)
    UNAUTHORIZED = 2000
    INVALID_TOKEN = 2001
    TOKEN_EXPIRED = 2002

    # Resource errors (3000-3099)
    NOT_FOUND = 3000
    ALREADY_EXISTS = 3001

    # User errors (3100-3199)
    USER_NOT_FOUND = 3100
    USER_ALREADY_EXISTS = 3101
    INVALID_EMAIL = 3102

    # Database errors (4000-4099)
    DATABASE_ERROR = 4000
    CONNECTION_ERROR = 4001

    # General errors (5000-5099)
    INTERNAL_ERROR = 5000
    SERVICE_UNAVAILABLE = 5001
