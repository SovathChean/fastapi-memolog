"""User service with business logic."""

from fastapi import Depends

from app.common.exceptions import NotFoundError, ValidationError
from app.common.mapper import FieldMapper
from app.models.domain.user import User
from app.models.schemas.user import UserCreate, UserUpdate
from app.repositories.user_repository import UserRepository
from app.services.base import BaseService
from app.support.user_support import UserSupport


class UserService(BaseService):
    """Service for user feature business logic."""

    def __init__(
        self,
        repository: UserRepository = Depends(),
        user_support: UserSupport = Depends(),
    ):
        """Initialize service with dependencies.

        Args:
            repository: User repository for data access.
            user_support: Support module for user logic.
        """
        super().__init__()
        self.repository = repository
        self.user_support = user_support

    async def create_user(self, data: UserCreate) -> User:
        """Create a new user.

        Args:
            data: User creation data.

        Returns:
            Created user entity.

        Raises:
            ValidationError: If validation fails or email already exists.
        """
        # Use FieldMapper for validation and transformation
        mapper = (
            FieldMapper(data)
            .validate("name", self.user_support.validate_name)
            .validate("email", self.user_support.validate_email)
            .transform("name", self.user_support.format_name)
            .transform("email", self.user_support.normalize_email)
        )
        user_data = mapper.to_dict()

        # Async check: email uniqueness (stays in service)
        existing_user = await self.repository.selectByEmail(user_data["email"])
        if existing_user:
            self.logger.warning(f"Email already exists: {user_data['email']}")
            raise ValidationError("Email already exists")

        # Create user
        user = User(**user_data)
        created_user = await self.repository.insert(user)

        self.logger.info(f"Created user: {created_user.id}")
        return created_user

    async def get_user(self, user_id: int) -> User:
        """Get user by ID.

        Args:
            user_id: User ID.

        Returns:
            User entity.

        Raises:
            NotFoundError: If user not found.
        """
        user = await self.repository.selectById(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        return user

    async def get_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Get all users with pagination.

        Args:
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            List of user entities.
        """
        return await self.repository.select(skip=skip, limit=limit)

    async def get_users_count(self) -> int:
        """Get total count of users.

        Returns:
            Total number of users.
        """
        return await self.repository.count()

    async def update_user(self, user_id: int, data: UserUpdate) -> User:
        """Update an existing user.

        Args:
            user_id: User ID.
            data: User update data.

        Returns:
            Updated user entity.

        Raises:
            NotFoundError: If user not found.
            ValidationError: If validation fails.
        """
        # Check if user exists
        existing_user = await self.repository.selectById(user_id)
        if not existing_user:
            raise NotFoundError("User", user_id)

        # Use FieldMapper for validation and transformation (only non-None fields)
        mapper = (
            FieldMapper(data)
            .validate("name", self.user_support.validate_name)
            .validate("email", self.user_support.validate_email)
            .transform("name", self.user_support.format_name)
            .transform("email", self.user_support.normalize_email)
        )
        update_data = mapper.to_dict()

        if not update_data:
            return existing_user

        # Async check: email uniqueness if email is being updated
        if "email" in update_data and update_data["email"] != existing_user.email:
            email_user = await self.repository.selectByEmail(update_data["email"])
            if email_user:
                raise ValidationError("Email already exists")

        updated_user = await self.repository.update(user_id, **update_data)
        self.logger.info(f"Updated user: {user_id}")
        return updated_user

    async def delete_user(self, user_id: int) -> bool:
        """Delete a user by ID.

        Args:
            user_id: User ID.

        Returns:
            True if deleted.

        Raises:
            NotFoundError: If user not found.
        """
        # Check if user exists
        existing_user = await self.repository.selectById(user_id)
        if not existing_user:
            raise NotFoundError("User", user_id)

        result = await self.repository.delete(user_id)
        self.logger.info(f"Deleted user: {user_id}")
        return result
