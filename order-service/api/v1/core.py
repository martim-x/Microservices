from api.dependencies.security import get_current_user
from fastapi import APIRouter, Depends

v1_router = APIRouter(
    prefix="/api/v1",
    tags=["v1"],
    dependencies=[Depends(get_current_user)],
)
