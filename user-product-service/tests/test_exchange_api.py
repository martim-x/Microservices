from api.dependencies.services import get_exchange_service
from api.exchange.core import exchange_router
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_exchange_currency() -> None:
    app = FastAPI()
    app.include_router(exchange_router)

    class DummyExchangeService:
        async def convert_price(
            self, *, price: float, from_currency: str, to_currency: str
        ):
            return {
                "provider": "dummy",
                "rate": 2.0,
                "converted_price": price * 2,
                "from_currency": from_currency,
                "to_currency": to_currency,
            }

        async def convertprice(
            self, *, price: float, fromcurrency: str, tocurrency: str
        ):
            return {
                "provider": "dummy",
                "rate": 2.0,
                "converted_price": price * 2,
                "from_currency": fromcurrency,
                "to_currency": tocurrency,
            }

    app.dependency_overrides[get_exchange_service] = lambda: DummyExchangeService()

    client = TestClient(app)
    response = client.get("/api/exchange/convert/convert/10/USD/EUR")

    assert response.status_code == 200
    assert response.json() == {
        "provider": "dummy",
        "rate": 2.0,
        "converted_price": 20.0,
        "from_currency": "USD",
        "to_currency": "EUR",
    }

    app.dependency_overrides = {}
