from api.app import (
    get_order_item_cache_service,
    get_order_item_write_service,
    get_service_token_service,
    limiter,
    v2_router,
)
from api.settings import settings
from database.schemas import OrderItemCreate, OrderItemOut
from fastapi import Depends, Request, status
from services.a_order_item_service import AOrderItemService
from services.a_service_token_service import AServiceTokenService
from services.cache.a_order_item_cache_service import AOrderItemCacheService


@v2_router.get(
    "/order-items",
    summary="Получить список позиций заказов (v2, Redis-кэш)",
    status_code=status.HTTP_200_OK,
    response_model=list[OrderItemOut],
)
@limiter.limit("100/minute")
async def v2_get_order_items(
    request: Request,
    order_item_cache: AOrderItemCacheService = Depends(get_order_item_cache_service),
):
    return await order_item_cache.get_cached_order_items()


@v2_router.get(
    "/order-items/{order_item_id}",
    summary="Получить позицию заказа по ID (v2, Redis-кэш)",
    status_code=status.HTTP_200_OK,
    response_model=OrderItemOut,
)
@limiter.limit("100/minute")
async def v2_get_order_item(
    request: Request,
    order_item_id: int,
    order_item_cache: AOrderItemCacheService = Depends(get_order_item_cache_service),
):
    return await order_item_cache.get_cached_order_item(order_item_id=order_item_id)


@v2_router.post(
    "/order-items",
    summary="Создать позицию заказа (v2, с инвалидацией кэша)",
    status_code=status.HTTP_201_CREATED,
    response_model=OrderItemOut,
)
@limiter.limit("20/minute")
async def v2_create_order_item(
    request: Request,
    new_order_item: OrderItemCreate,
    order_item_service: AOrderItemService = Depends(get_order_item_write_service),
    order_item_cache: AOrderItemCacheService = Depends(get_order_item_cache_service),
    service_token_service: AServiceTokenService = Depends(get_service_token_service),
):
    service_access_token = await service_token_service.issue_service_access_token(
        service_name=settings.ORDER_SERVICE_NAME,
        service_secret=settings.SERVICE_SECRET_KEY,
        audience=settings.USER_PRODUCT_SERVICE_NAME,
    )
    order_item = await order_item_service.create_order_item(
        new_order_item=new_order_item,
        service_access_token=service_access_token,
    )
    await order_item_cache.invalidate_order_items()
    return order_item


@v2_router.delete(
    "/order-items/{order_item_id}",
    summary="Удалить позицию заказа (v2, с инвалидацией кэша)",
    status_code=status.HTTP_204_NO_CONTENT,
)
@limiter.limit("10/minute")
async def v2_delete_order_item(
    request: Request,
    order_item_id: int,
    order_item_service: AOrderItemService = Depends(get_order_item_write_service),
    order_item_cache: AOrderItemCacheService = Depends(get_order_item_cache_service),
):
    if await order_item_service.delete_order_item_by_id(order_item_id=order_item_id):
        await order_item_cache.invalidate_order_item(order_item_id=order_item_id)
        await order_item_cache.invalidate_order_items()
