from api.app import (
    cache_dep,
    get_order_read_service,
    get_order_write_service,
    get_service_token_service,
    limiter,
    v1_router,
)
from api.settings import settings
from database.schemas import OrderCreate, OrderOut
from fastapi import Depends, Request, status
from services.a_order_service import AOrderService
from services.a_service_token_service import AServiceTokenService


@v1_router.get(
    "/orders",
    summary="Получить список заказов",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(cache_dep())],
    response_model=list[OrderOut],
)
@limiter.limit("100/minute")
async def v1_get_orders(
    request: Request,
    order_service: AOrderService = Depends(get_order_read_service),
):
    return await order_service.get_orders()


@v1_router.get(
    "/orders/{order_id}",
    summary="Получить заказ по ID",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(cache_dep())],
    response_model=OrderOut,
)
@limiter.limit("100/minute")
async def v1_get_order(
    request: Request,
    order_id: int,
    order_service: AOrderService = Depends(get_order_read_service),
):
    return await order_service.get_order_by_id(order_id=order_id)


@v1_router.post(
    "/orders",
    summary="Создать заказ",
    status_code=status.HTTP_201_CREATED,
    response_model=OrderOut,
)
@limiter.limit("20/minute")
async def v1_create_order(
    request: Request,
    new_order: OrderCreate,
    order_service: AOrderService = Depends(get_order_write_service),
    service_token_service: AServiceTokenService = Depends(get_service_token_service),
):
    service_access_token = await service_token_service.issue_service_access_token(
        service_name=settings.ORDER_SERVICE_NAME,
        service_secret=settings.SERVICE_SECRET_KEY,
        audience=settings.USER_PRODUCT_SERVICE_NAME,
    )
    return await order_service.create_order(
        new_order=new_order,
        service_access_token=service_access_token,
    )


@v1_router.delete(
    "/orders/{order_id}",
    summary="Удалить заказ",
    status_code=status.HTTP_204_NO_CONTENT,
)
@limiter.limit("10/minute")
async def v1_delete_order(
    request: Request,
    order_id: int,
    order_service: AOrderService = Depends(get_order_write_service),
):
    await order_service.delete_order_by_id(order_id=order_id)
