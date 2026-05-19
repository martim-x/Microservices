from api.dependencies.limiter import limiter
from api.dependencies.services import (
    get_product_cache_service,
    get_product_write_service,
)
from database.schemas import ProductCreate, ProductOut, ProductUpdate
from fastapi import APIRouter, Depends, Request, status
from services.a_product_service import AProductService
from services.cache.a_product_cache_service import AProductCacheService

products_router = APIRouter(prefix="/products")


@products_router.get(
    "/",
    summary="Получить список товаров (v2, Redis-кэш)",
    status_code=status.HTTP_200_OK,
    response_model=list[ProductOut],
)
@limiter.limit("100/minute")
async def v2_get_products(
    request: Request,
    product_cache: AProductCacheService = Depends(get_product_cache_service),
):
    return await product_cache.get_cached_products()


@products_router.get(
    "/{product_id}",
    summary="Получить товар по ID (v2, Redis-кэш)",
    status_code=status.HTTP_200_OK,
    response_model=ProductOut,
)
@limiter.limit("100/minute")
async def v2_get_product(
    request: Request,
    product_id: int,
    product_cache: AProductCacheService = Depends(get_product_cache_service),
):
    return await product_cache.get_cached_product(product_id=product_id)


@products_router.post(
    "/",
    summary="Создать товар (v2, с инвалидацией кэша)",
    status_code=status.HTTP_201_CREATED,
    response_model=ProductOut,
)
@limiter.limit("20/minute")
async def v2_create_product(
    request: Request,
    new_product: ProductCreate,
    product_service: AProductService = Depends(get_product_write_service),
    product_cache: AProductCacheService = Depends(get_product_cache_service),
):
    product = await product_service.create_product(new_product=new_product)
    await product_cache.invalidate_products()

    return product


@products_router.put(
    "/{product_id}",
    summary="Обновить товар (v2, с инвалидацией кэша)",
    status_code=status.HTTP_200_OK,
    response_model=ProductOut,
)
@limiter.limit("20/minute")
async def v2_update_product(
    request: Request,
    product_id: int,
    new_product: ProductUpdate,
    product_service: AProductService = Depends(get_product_write_service),
    product_cache: AProductCacheService = Depends(get_product_cache_service),
):
    await product_cache.invalidate_product(product_id=product_id)
    await product_cache.invalidate_products()

    return await product_service.update_product(
        product_id=product_id,
        new_product=new_product,
    )


@products_router.delete(
    "/{product_id}",
    summary="Удалить товар (v2, с инвалидацией кэша)",
    status_code=status.HTTP_204_NO_CONTENT,
)
@limiter.limit("10/minute")
async def v2_delete_product(
    request: Request,
    product_id: int,
    product_service: AProductService = Depends(get_product_write_service),
    product_cache: AProductCacheService = Depends(get_product_cache_service),
):
    await product_service.delete_product_by_id(product_id=product_id)

    await product_cache.invalidate_product(product_id=product_id)
    await product_cache.invalidate_products()
