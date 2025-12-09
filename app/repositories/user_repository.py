"""User repository for data access."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.user import User
from app.repositories.base import SQLAlchemyRepository
from config.database import get_db


class UserRepository(SQLAlchemyRepository[User]):
    """Repository for User entity database operations."""

    def __init__(self, session: AsyncSession = Depends(get_db)):
        """Initialize repository with database session.

        Args:
            session: Async database session.
        """
        super().__init__(session, User)

    async def selectByEmail(self, email: str) -> User | None:
        """Get user by email address.

        Args:
            email: User's email address.

        Returns:
            User if found, None otherwise.
        """
        return await self.selectOne(email=email)
