from sqlalchemy.orm import Mapped
from sqlalchemy.testing.schema import mapped_column

from app.models.domain.base import BaseEntity


class Product(BaseEntity):
    __tablename__ = 'products'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str] = mapped_column(unique=True)
