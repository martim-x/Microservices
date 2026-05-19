from api.dependencies.security import get_current_user
from api.v2.products import products_router
from api.v2.users import users_router
from fastapi import APIRouter, Depends

v2_router = APIRouter(
    prefix="/api/v2",
    tags=["v2"],
    dependencies=[Depends(get_current_user)],
)

for router in [products_router, users_router]:
    v2_router.include_router(router=router)
