from fastapi import APIRouter

health_router = APIRouter(
    prefix="/api/health",
    tags=["health"],
)
