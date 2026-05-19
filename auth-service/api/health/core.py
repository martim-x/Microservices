from api.health.health import local_router
from fastapi import APIRouter

health_router = APIRouter(
    prefix="/api/health",
    tags=["health"],
)


for router in [local_router]:
    health_router.include_router(router=router)
