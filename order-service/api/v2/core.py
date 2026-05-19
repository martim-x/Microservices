from api.dependencies.security import get_current_user
from api.v2.order_items import order_items_router
from api.v2.orders import orders_router
from fastapi import APIRouter, Depends

v2_router = APIRouter(
    prefix="/api/v2",
    tags=["v2"],
    dependencies=[Depends(get_current_user)],
)

for router in [orders_router, order_items_router]:
    v2_router.include_router(router=router)
