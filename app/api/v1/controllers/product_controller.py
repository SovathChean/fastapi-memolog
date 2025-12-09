from fastapi.params import Depends

from app.common import ResponseMessage, handle_request
from app.models.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services.product_service import ProductService


class ProductController:
    def __init__(self, service: ProductService = Depends()):
        self.service = service

    async def create(self, request: ProductCreate) -> ResponseMessage[ProductResponse]:
        return await handle_request(
            action=lambda: self.service.create(request),
            response_model=ProductResponse,
            success_message="Product created successfully",
        )

    async def get_by_id(self, product_id: int) -> ResponseMessage[ProductResponse]:
        return await handle_request(
            action=lambda: self.service.get_by_id(product_id),
            response_model=ProductResponse,
            success_message="Product found successfully",
        )

    async def update_by_id(
        self, product_id: int, data: ProductUpdate
    ) -> ResponseMessage[ProductResponse]:
        return await handle_request(
            action=lambda: self.service.update_by_id(product_id, data),
            response_model=ProductResponse,
            success_message="Product updated successfully",
        )

    async def delete(self, product_id: int) -> ResponseMessage[None]:

        return await handle_request(
            action=lambda: self.service.delete_by_id(product_id),
            success_message="Product deleted successfully",
        )
