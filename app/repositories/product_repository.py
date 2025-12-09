from fastapi import Depends
from sqlalchemy.ext.asyncio.session import AsyncSession

from app.models.domain.product import Product
from app.repositories.base import SQLAlchemyRepository
from config.database import get_db


class ProductRepository(SQLAlchemyRepository[Product]):

    def __init__(self, session: AsyncSession = Depends(get_db)):
        super().__init__(session, Product)

    async def find_by_name(self, name: str) -> Product | None:
        """Get product by name.
        Args:
            name: Product's name.
        """
        return await self.selectOne(name=name)




