from fastapi import Depends

from app.common.exceptions import NotFoundError, ValidationError
from app.common.mapper import FieldMapper
from app.models.domain.product import Product
from app.models.schemas.product import ProductCreate, ProductUpdate
from app.repositories.product_repository import ProductRepository
from app.services.base import BaseService


class ProductService(BaseService):

    def __init__(self, repository: ProductRepository = Depends()):
        self.repository = repository
        super().__init__()

    async def get_by_id(self, id: int) -> Product | None:

        product = await self.repository.selectById(id)
        if not product:
            raise NotFoundError("Product", id)
        return product

    async def create(self, data: ProductCreate) -> Product:

        product_by_name= await self.repository.selectOne(name=data.name)
        if product_by_name:
            self.logger.warning(f"Product already exists: {product_by_name}")
            raise ValidationError("Product already exists")

        product_data = FieldMapper(data).to_dict()

        product = Product(**product_data)

        product = await self.repository.insert(product)

        return product

    async def delete_by_id(self, id: int) -> None:

        product = await self.repository.selectById(id)
        if not product:
            raise NotFoundError("Product", id)

        await self.repository.delete(id)
        self.logger.info(f"Deleted product: {id}")

    async def update_by_id(self, product_id: int, data: ProductUpdate) -> Product | None:

        product = await self.repository.selectById(product_id)
        if not product:
            raise NotFoundError("Product", product_id)

        product_data = FieldMapper(data).to_dict()

        update_data = await self.repository.update(product_id, **product_data)

        return update_data




