"""User controller for handling HTTP requests."""

from fastapi import Depends

from app.common.response import ResponseMessage, handle_request
from app.models.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user_service import UserService


class UserController:
    """Controller for user feature endpoints.

    Handles HTTP request/response processing and coordinates with services.
    """

    def __init__(
        self,
        service: UserService = Depends(),
    ):
        """Initialize controller with dependencies.

        Args:
            service: User service for business logic.
        """
        self.service = service

    async def create(self, data: UserCreate) -> ResponseMessage[UserResponse]:
        """Create a new user.

        Args:
            data: User creation request data.

        Returns:
            ResponseMessage containing UserResponse or error.
        """
        return await handle_request(
            action=lambda: self.service.create_user(data),
            response_model=UserResponse,
            success_message="User created successfully",
        )

    async def get_by_id(self, user_id: int) -> ResponseMessage[UserResponse]:
        """Get user by ID.

        Args:
            user_id: User ID.

        Returns:
            ResponseMessage containing UserResponse or error.
        """
        return await handle_request(
            action=lambda: self.service.get_user(user_id),
            response_model=UserResponse,
        )

    async def get_all(
        self, skip: int = 0, limit: int = 100
    ) -> ResponseMessage[list[UserResponse]]:
        """Get all users with pagination.

        Args:
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            ResponseMessage containing list of UserResponse.
        """
        from app.common.constants import ErrorCodes
        from app.common.response import ResponseBuilder

        try:
            users = await self.service.get_users(skip=skip, limit=limit)
            total = await self.service.get_users_count()

            user_responses = [UserResponse.model_validate(user) for user in users]

            total_pages = (total + limit - 1) // limit if limit > 0 else 0
            current_page = (skip // limit) + 1 if limit > 0 else 1

            return (
                ResponseBuilder[list[UserResponse]]()
                .success()
                .add_data(user_responses)
                .add_page(
                    total_pages=total_pages,
                    page=current_page,
                    page_size=limit,
                    total_items=total,
                )
                .build_paginated()
            )
        except Exception as e:
            return (
                ResponseBuilder[list[UserResponse]]()
                .fail()
                .add_error_code(ErrorCodes.INTERNAL_ERROR)
                .add_error_message(str(e))
                .build()
            )

    async def update(
        self, user_id: int, data: UserUpdate
    ) -> ResponseMessage[UserResponse]:
        """Update an existing user.

        Args:
            user_id: User ID.
            data: User update request data.

        Returns:
            ResponseMessage containing UserResponse or error.
        """
        return await handle_request(
            action=lambda: self.service.update_user(user_id, data),
            response_model=UserResponse,
            success_message="User updated successfully",
        )

    async def delete(self, user_id: int) -> ResponseMessage[None]:
        """Delete a user by ID.

        Args:
            user_id: User ID.

        Returns:
            ResponseMessage with success or error.
        """
        return await handle_request(
            action=lambda: self.service.delete_user(user_id),
            success_message="User deleted successfully",
        )
