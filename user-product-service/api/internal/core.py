from api.dependencies.security import get_current_service
from fastapi import APIRouter, Depends

internal_router = APIRouter(
    prefix="/api/internal",
    tags=["internal"],
    dependencies=[Depends(get_current_service)],
)
