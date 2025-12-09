"""User domain model."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.domain.base import BaseEntity


class User(BaseEntity):
    """User entity representing a user in the system."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)