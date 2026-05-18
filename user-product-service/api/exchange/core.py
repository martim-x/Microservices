from fastapi import APIRouter

exchange_router = APIRouter(
    prefix="/api/exchange",
    tags=["exchange"],
)
