"""Health check routes."""

from fastapi import APIRouter

from app.common.response import ResponseBuilder, ResponseMessage
from app.models.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/",
    response_model=ResponseMessage[HealthResponse],
    summary="Health check",
    description="Check if the service is running",
)
async def health_check() -> ResponseMessage[HealthResponse]:
    """Health check endpoint.

    Returns:
        ResponseMessage containing HealthResponse with status OK.
    """
    return (
        ResponseBuilder[HealthResponse]()
        .success()
        .add_data(HealthResponse(status="OK"))
        .build()
    )


@router.get(
    "/health",
    response_model=ResponseMessage[HealthResponse],
    summary="Detailed health check",
    description="Get detailed health status",
)
async def detailed_health_check() -> ResponseMessage[HealthResponse]:
    """Detailed health check endpoint.

    Returns:
        ResponseMessage containing HealthResponse with status and message.
    """
    return (
        ResponseBuilder[HealthResponse]()
        .success()
        .add_data(
            HealthResponse(
                status="OK",
                message="All systems operational",
            )
        )
        .add_message("Health check passed")
        .build()
    )
