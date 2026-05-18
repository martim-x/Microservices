from api.app import (
    cache_dep,
    get_order_item_read_service,
    get_order_item_write_service,
    get_service_token_service,
    limiter,
    v1_router,
)
from api.settings import settings
from database.schemas import OrderItemCreate, OrderItemOut
from fastapi import Depends, Request, status
from services.a_order_item_service import AOrderItemService
from services.a_service_token_service import AServiceTokenService


@v1_router.get(
    "/order-items",
    summary="Получить список позиций заказов",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(cache_dep())],
    response_model=list[OrderItemOut],
)
@limiter.limit("100/minute")
async def v1_get_order_items(
    request: Request,
    order_item_service: AOrderItemService = Depends(get_order_item_read_service),
):
    return await order_item_service.get_order_items()


@v1_router.get(
    "/order-items/{order_item_id}",
    summary="Получить позицию заказа по ID",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(cache_dep())],
    response_model=OrderItemOut,
)
@limiter.limit("100/minute")
async def v1_get_order_item(
    request: Request,
    order_item_id: int,
    order_item_service: AOrderItemService = Depends(get_order_item_read_service),
):
    return await order_item_service.get_order_item_by_id(order_item_id=order_item_id)


@v1_router.post(
    "/order-items",
    summary="Создать позицию заказа",
    status_code=status.HTTP_201_CREATED,
    response_model=OrderItemOut,
)
@limiter.limit("20/minute")
async def v1_create_order_item(
    request: Request,
    new_order_item: OrderItemCreate,
    order_item_service: AOrderItemService = Depends(get_order_item_write_service),
    service_token_service: AServiceTokenService = Depends(get_service_token_service),
):
    service_access_token = await service_token_service.issue_service_access_token(
        service_name=settings.ORDER_SERVICE_NAME,
        service_secret=settings.SERVICE_SECRET_KEY,
        audience=settings.USER_PRODUCT_SERVICE_NAME,
    )
    return await order_item_service.create_order_item(
        new_order_item=new_order_item,
        service_access_token=service_access_token,
    )


@v1_router.delete(
    "/order-items/{order_item_id}",
    summary="Удалить позицию заказа",
    status_code=status.HTTP_204_NO_CONTENT,
)
@limiter.limit("10/minute")
async def v1_delete_order_item(
    request: Request,
    order_item_id: int,
    order_item_service: AOrderItemService = Depends(get_order_item_write_service),
):
    await order_item_service.delete_order_item_by_id(order_item_id=order_item_id)
