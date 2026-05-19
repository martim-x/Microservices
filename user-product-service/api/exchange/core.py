from api.exchange.exchange import convert_router
from fastapi import APIRouter

exchange_router = APIRouter(
    prefix="/api/exchange",
    tags=["exchange"],
)

for router in [convert_router]:
    exchange_router.include_router(router=router)
