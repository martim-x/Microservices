from api.app import (
    cache_dep,
    get_product_read_service,
    get_product_write_service,
    limiter,
    v1_router,
)
from database.schemas import ProductCreate, ProductOut, ProductUpdate
from fastapi import Depends, Request, status
from services.a_product_service import AProductService


@v1_router.get(
    "/products",
    summary="Получить список товаров",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(cache_dep())],
    response_model=list[ProductOut],
)
@limiter.limit("100/minute")
async def v1_get_products(
    request: Request,
    product_service: AProductService = Depends(get_product_read_service),
):
    return await product_service.get_products()


@v1_router.get(
    "/products/{product_id}",
    summary="Получить товар по ID",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(cache_dep())],
    response_model=ProductOut,
)
@limiter.limit("100/minute")
async def v1_get_product(
    request: Request,
    product_id: int,
    product_service: AProductService = Depends(get_product_read_service),
):
    return await product_service.get_product_by_id(product_id=product_id)


@v1_router.post(
    "/products",
    summary="Создать товар",
    status_code=status.HTTP_201_CREATED,
    response_model=ProductOut,
)
@limiter.limit("20/minute")
async def v1_create_product(
    request: Request,
    new_product: ProductCreate,
    product_service: AProductService = Depends(get_product_write_service),
):
    return await product_service.create_product(new_product=new_product)


@v1_router.put(
    "/products/{product_id}",
    summary="Обновить товар",
    status_code=status.HTTP_200_OK,
    response_model=ProductOut,
)
@limiter.limit("10/minute")
async def v1_update_product(
    request: Request,
    product_id: int,
    new_product: ProductUpdate,
    product_service: AProductService = Depends(get_product_write_service),
):
    return await product_service.update_product(
        product_id=product_id,
        new_product=new_product,
    )


@v1_router.delete(
    "/products/{product_id}",
    summary="Удалить товар",
    status_code=status.HTTP_204_NO_CONTENT,
)
@limiter.limit("10/minute")
async def v1_delete_product(
    request: Request,
    product_id: int,
    product_service: AProductService = Depends(get_product_write_service),
):
    await product_service.delete_product_by_id(product_id=product_id)
