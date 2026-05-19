from api.dependencies.services import get_exchange_service
from fastapi import APIRouter, Depends, Request
from services.a_exchange_service import AExchangeService

convert_router = APIRouter(prefix="/convert")


@convert_router.get("/convert/{price}/{from_currency}/{to_currency}")
async def exchange_currency(
    request: Request,
    price: float,
    from_currency: str,
    to_currency: str,
    exchange_service: AExchangeService = Depends(get_exchange_service),
):
    return await exchange_service.convert_price(
        price=price,
        from_currency=from_currency,
        to_currency=to_currency,
    )
