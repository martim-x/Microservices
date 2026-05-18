from api.dependencies.security import get_current_user
from fastapi import APIRouter, Depends

v2_router = APIRouter(
    prefix="/api/v2",
    tags=["v2"],
    dependencies=[Depends(get_current_user)],
)
