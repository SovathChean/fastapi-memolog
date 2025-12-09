"""User feature routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.v1.controllers.user_controller import UserController
from app.common.response import PaginatedResponse, ResponseMessage
from app.models.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.post(
    "/",
    response_model=ResponseMessage[UserResponse],
    summary="Create a new user",
    description="Create a new user with name and email",
    status_code=201,
)
async def create_user(
    request: UserCreate,
    controller: UserController = Depends(),
) -> ResponseMessage[UserResponse]:
    """Create a new user.

    Args:
        request: User creation request body.
        controller: User controller instance.

    Returns:
        ResponseMessage containing created UserResponse.
    """
    return await controller.create(request)


@router.get(
    "/{user_id}",
    response_model=ResponseMessage[UserResponse],
    summary="Get user by ID",
    description="Retrieve a user by their ID",
)
async def get_user(
    user_id: Annotated[int, Path(description="User ID", ge=1)],
    controller: UserController = Depends(),
) -> ResponseMessage[UserResponse]:
    """Get user by ID.

    Args:
        user_id: User ID.
        controller: User controller instance.

    Returns:
        ResponseMessage containing UserResponse.
    """
    return await controller.get_by_id(user_id)


@router.get(
    "/",
    response_model=PaginatedResponse[UserResponse],
    summary="List all users",
    description="Retrieve all users with pagination",
)
async def list_users(
    skip: Annotated[
        int,
        Query(
            ge=0,
            description="Number of records to skip",
        ),
    ] = 0,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
            description="Maximum number of records to return",
        ),
    ] = 20,
    controller: UserController = Depends(),
) -> PaginatedResponse[UserResponse]:
    """List all users with pagination.

    Args:
        skip: Number of records to skip.
        limit: Maximum number of records to return.
        controller: User controller instance.

    Returns:
        PaginatedResponse containing list of UserResponse.
    """
    return await controller.get_all(skip=skip, limit=limit)


@router.put(
    "/{user_id}",
    response_model=ResponseMessage[UserResponse],
    summary="Update a user",
    description="Update an existing user by ID",
)
async def update_user(
    user_id: Annotated[int, Path(description="User ID", ge=1)],
    request: UserUpdate,
    controller: UserController = Depends(),
) -> ResponseMessage[UserResponse]:
    """Update an existing user.

    Args:
        user_id: User ID.
        request: User update request body.
        controller: User controller instance.

    Returns:
        ResponseMessage containing updated UserResponse.
    """
    return await controller.update(user_id, request)


@router.delete(
    "/{user_id}",
    response_model=ResponseMessage[None],
    summary="Delete a user",
    description="Delete a user by ID",
)
async def delete_user(
    user_id: Annotated[int, Path(description="User ID", ge=1)],
    controller: UserController = Depends(),
) -> ResponseMessage[None]:
    """Delete a user by ID.

    Args:
        user_id: User ID.
        controller: User controller instance.

    Returns:
        ResponseMessage with success or error.
    """
    return await controller.delete(user_id)
