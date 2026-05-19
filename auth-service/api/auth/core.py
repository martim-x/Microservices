from api.auth.auth import local_router
from fastapi import APIRouter

auth_router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
)

for router in [local_router]:
    auth_router.include_router(router=router)
