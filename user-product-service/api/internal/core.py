from api.dependencies.security import get_current_service
from api.internal.products import products_router
from api.internal.users import users_router
from fastapi import APIRouter, Depends

internal_router = APIRouter(
    prefix="/api/internal",
    tags=["internal"],
    dependencies=[Depends(get_current_service)],
)

for router in [products_router, users_router]:
    internal_router.include_router(router=router)
