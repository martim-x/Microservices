from api.dependencies.security import get_current_user
from api.v1.products import products_router
from api.v1.users import users_router
from fastapi import APIRouter, Depends

v1_router = APIRouter(
    prefix="/api/v1",
    tags=["v1"],
    dependencies=[Depends(get_current_user)],
)


for router in [products_router, users_router]:
    v1_router.include_router(router=router)
