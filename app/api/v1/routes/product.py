from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.api.v1.controllers.product_controller import ProductController
from app.common import ResponseMessage
from app.models.schemas.product import ProductCreate, ProductResponse, ProductUpdate

router = APIRouter(prefix="/products", tags=["Products]"])

@router.post(
    "/",
    response_model=ResponseMessage[ProductResponse],
    summary="Create a new product",
    status_code=201,
    description="Product creation",
)

async def create_product(
        request: ProductCreate,
        controller: ProductController = Depends(),
) -> ResponseMessage[ProductResponse]:

    return await controller.create(request)

@router.get(
    "/{product_id}",
    response_model=ResponseMessage[ProductResponse],
)

async def get_product(
        product_id: Annotated[int, Path(description="Product ID", ge=1)],
        controller: ProductController = Depends()) -> ResponseMessage[ProductResponse]:

    return await controller.get_by_id(product_id)

@router.put(
    "/{product_id}",
    response_model=ResponseMessage[ProductResponse],
    summary="Update a product",
)
async def update_product(
        product_id: Annotated[int, Path(description="Product Id", ge=1)],
        request: ProductUpdate,
        controller: ProductController = Depends()) -> ResponseMessage[ProductResponse]:

    return await controller.update_by_id(product_id, request)

@router.delete(
    path="/{product_id}",
    response_model=ResponseMessage[None],
    summary="Delete a product",
)

async def delete_product(
        product_id: Annotated[int, Path(description="Product Id", ge=1)],
        controller: ProductController = Depends())->ResponseMessage[None]:

    return await controller.delete(product_id)
