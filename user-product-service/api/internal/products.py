from api.dependencies.limiter import limiter
from api.dependencies.services import get_product_cache_service
from database.schemas import ProductOut
from fastapi import APIRouter, Depends, Request, status
from services.cache.a_product_cache_service import AProductCacheService

products_router = APIRouter(prefix="/products")


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
