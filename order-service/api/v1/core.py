from api.dependencies.security import get_current_user
from api.v1.order_items import order_items_router
from api.v1.orders import orders_router
from fastapi import APIRouter, Depends

v1_router = APIRouter(
    prefix="/api/v1",
    tags=["v1"],
    dependencies=[Depends(get_current_user)],
)

for router in [order_items_router, orders_router]:
    v1_router.include_router(router=router)
