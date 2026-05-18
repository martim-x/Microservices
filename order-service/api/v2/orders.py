from api.app import (
    get_message_queue_service,
    get_order_cache_service,
    get_order_write_service,
    get_service_token_service,
    limiter,
    v2_router,
)
from api.settings import settings
from database.schemas import OrderCreate, OrderOut, ReportCreate
from fastapi import Depends, Request, status
from services.a_message_queue_service import AMessageQueueService
from services.a_order_service import AOrderService
from services.a_service_token_service import AServiceTokenService
from services.cache.a_order_cache_service import AOrderCacheService


@v2_router.get(
    "/orders",
    summary="Получить список заказов (v2, Redis-кэш)",
    status_code=status.HTTP_200_OK,
    response_model=list[OrderOut],
)
@limiter.limit("100/minute")
async def v2_get_orders(
    request: Request,
    order_cache: AOrderCacheService = Depends(get_order_cache_service),
):
    return await order_cache.get_cached_orders()


@v2_router.get(
    "/orders/{order_id}",
    summary="Получить заказ по ID (v2, Redis-кэш)",
    status_code=status.HTTP_200_OK,
    response_model=OrderOut,
)
@limiter.limit("100/minute")
async def v2_get_order(
    request: Request,
    order_id: int,
    order_cache: AOrderCacheService = Depends(get_order_cache_service),
):
    return await order_cache.get_cached_order(order_id=order_id)


@v2_router.post(
    "/orders",
    summary="Создать заказ (v2, с инвалидацией кэша)",
    status_code=status.HTTP_201_CREATED,
    response_model=OrderOut,
)
@limiter.limit("20/minute")
async def v2_create_order(
    request: Request,
    new_order: OrderCreate,
    order_service: AOrderService = Depends(get_order_write_service),
    order_cache: AOrderCacheService = Depends(get_order_cache_service),
    service_token_service: AServiceTokenService = Depends(get_service_token_service),
    message_queue_service: AMessageQueueService = Depends(get_message_queue_service),
):
    service_access_token = await service_token_service.issue_service_access_token(
        service_name=settings.ORDER_SERVICE_NAME,
        service_secret=settings.SERVICE_SECRET_KEY,
        audience=settings.USER_PRODUCT_SERVICE_NAME,
    )
    order = await order_service.create_order(
        new_order=new_order,
        service_access_token=service_access_token,
    )
    report = ReportCreate(
        order_id=order.id,
        user_id=order.user_id,
        total=order.total,
    )

    await message_queue_service.produce_report(report)
    await order_cache.invalidate_orders()
    return order


@v2_router.delete(
    "/orders/{order_id}",
    summary="Удалить заказ (v2, с инвалидацией кэша)",
    status_code=status.HTTP_204_NO_CONTENT,
)
@limiter.limit("10/minute")
async def v2_delete_order(
    request: Request,
    order_id: int,
    order_service: AOrderService = Depends(get_order_write_service),
    order_cache: AOrderCacheService = Depends(get_order_cache_service),
):
    if await order_service.delete_order_by_id(order_id=order_id):
        await order_cache.invalidate_order(order_id=order_id)
        await order_cache.invalidate_orders()
