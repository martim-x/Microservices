from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from services.exceptions import NotFoundError, ServiceError, ValidationServiceError


def test_app_metadata() -> None:
    from api.app import app
    from api.settings import settings

    assert app.title == settings.ORDER_SERVICE_NAME
    assert app.version == settings.ORDER_SERVICE_VERSION


def test_process_time_header_middleware() -> None:
    from api.app import add_process_time_header

    app = FastAPI()

    @app.get("/ping")
    async def ping() -> dict[str, bool]:
        return {"ok": True}

    app.middleware("http")(add_process_time_header)

    client = TestClient(app)
    response = client.get("/ping")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert "X-Process-Time" in response.headers


def test_error_handler_service_error() -> None:
    from api.app import error_handler

    app = FastAPI()

    @app.get("/boom")
    async def boom() -> None:
        raise ServiceError(status_code=418, detail="service boom")

    app.middleware("http")(error_handler)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom")

    assert response.status_code == 418
    assert response.json() == {"detail": "service boom"}


def test_error_handler_http_exception() -> None:
    from api.app import error_handler

    app = FastAPI()

    @app.get("/boom")
    async def boom() -> None:
        raise HTTPException(status_code=404, detail="missing")

    app.middleware("http")(error_handler)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom")

    assert response.status_code == 404
    assert response.json() == {"detail": "missing"}


def test_error_handler_generic_exception() -> None:
    from api.app import error_handler

    app = FastAPI()

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("unexpected")

    app.middleware("http")(error_handler)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {"detail": "Внутренняя ошибка сервера"}


@pytest.mark.asyncio
async def test_lifespan_initializes_services(monkeypatch: pytest.MonkeyPatch) -> None:
    from api import app as app_module

    app = FastAPI()

    redis_client = AsyncMock()
    monkeypatch.setattr(
        app_module.aioredis,
        "from_url",
        AsyncMock(return_value=redis_client),
    )

    connection = AsyncMock()
    channel = AsyncMock()
    connection.channel.return_value = channel
    channel.is_closed = False
    connection.is_closed = False

    async def fake_connect_robust(url: str) -> AsyncMock:
        return connection

    monkeypatch.setattr(
        app_module.aio_pika,
        "connect_robust",
        fake_connect_robust,
    )

    repo_instance = AsyncMock()
    repo_instance.db_get_service_token_by_name.return_value = None

    service_instance = AsyncMock()
    service_instance.register_service = AsyncMock()

    class DummySession:
        async def __aenter__(self) -> AsyncMock:
            return AsyncMock()

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

    monkeypatch.setattr(app_module, "SessionLocalMaster", lambda: DummySession())
    monkeypatch.setattr(
        app_module,
        "AServiceTokenRepository",
        lambda session: repo_instance,
    )
    monkeypatch.setattr(
        app_module,
        "AServiceTokenService",
        lambda service_token_repository: service_instance,
    )

    async with app_module.lifespan(app):
        health = app.state.services["health"]
        assert health["startup_complete"] is True
        assert health["shutdown_requested"] is False

        checks = health["checks"]
        assert checks[app_module.settings.DB_SERVICE_NAME]["ok"] is True
        assert checks[app_module.settings.CACHE_SERVICE_NAME]["ok"] is True
        assert checks[app_module.settings.ORDER_SERVICE_NAME]["ok"] is True
        assert checks[app_module.settings.MQ_SERVICE_NAME]["ok"] is True

        assert app.state.redis_client is redis_client
        assert app.state.rabbitmq_connection is connection
        assert app.state.rabbitmq_channel is channel
        assert app.state.message_queue_service is not None

    assert app.state.services["health"]["shutdown_requested"] is True
    repo_instance.db_get_service_token_by_name.assert_awaited_once_with(
        service_name=app_module.settings.ORDER_SERVICE_NAME,
    )
    service_instance.register_service.assert_awaited_once()
    channel.set_qos.assert_awaited_once_with(prefetch_count=1)
    channel.declare_queue.assert_awaited_once_with(
        name=app_module.settings.RABBITMQ_ROUTING_KEY,
        durable=True,
    )
    channel.close.assert_awaited_once()
    connection.close.assert_awaited_once()
    redis_client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_lifespan_skips_service_registration_if_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from api import app as app_module

    app = FastAPI()

    redis_client = AsyncMock()
    monkeypatch.setattr(
        app_module.aioredis,
        "from_url",
        AsyncMock(return_value=redis_client),
    )

    connection = AsyncMock()
    channel = AsyncMock()
    channel.is_closed = False
    connection.is_closed = False
    connection.channel.return_value = channel

    async def fake_connect_robust(url: str) -> AsyncMock:
        return connection

    monkeypatch.setattr(
        app_module.aio_pika,
        "connect_robust",
        fake_connect_robust,
    )

    repo_instance = AsyncMock()
    repo_instance.db_get_service_token_by_name.return_value = object()

    service_instance = AsyncMock()
    service_instance.register_service = AsyncMock()

    class DummySession:
        async def __aenter__(self) -> AsyncMock:
            return AsyncMock()

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

    monkeypatch.setattr(app_module, "SessionLocalMaster", lambda: DummySession())
    monkeypatch.setattr(
        app_module,
        "AServiceTokenRepository",
        lambda session: repo_instance,
    )
    monkeypatch.setattr(
        app_module,
        "AServiceTokenService",
        lambda service_token_repository: service_instance,
    )

    async with app_module.lifespan(app):
        assert app.state.services["health"]["startup_complete"] is True

    service_instance.register_service.assert_not_awaited()
    channel.close.assert_awaited_once()
    connection.close.assert_awaited_once()
    redis_client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_order_service_get_order_by_id_success() -> None:
    from services.a_order_service import AOrderService

    repo = AsyncMock()
    repo.db_get_order_by_id.return_value = SimpleNamespace(
        id=1,
        user_id=2,
        total=Decimal("10.50"),
        created_at="2026-01-01T00:00:00",
    )

    service = AOrderService(order_repository=repo)

    result = await service.get_order_by_id(order_id=1)

    assert result.id == 1
    repo.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_order_service_get_order_by_id_not_found() -> None:
    from services.a_order_service import AOrderService

    repo = AsyncMock()
    repo.db_get_order_by_id.return_value = None

    service = AOrderService(order_repository=repo)

    with pytest.raises(NotFoundError):
        await service.get_order_by_id(order_id=1)

    repo.session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_order_service_get_orders_success() -> None:
    from services.a_order_service import AOrderService

    repo = AsyncMock()
    repo.db_get_orders.return_value = [
        SimpleNamespace(
            id=1,
            user_id=2,
            total=Decimal("10.50"),
            created_at="2026-01-01T00:00:00",
        ),
        SimpleNamespace(
            id=2,
            user_id=3,
            total=Decimal("20.00"),
            created_at="2026-01-01T00:00:00",
        ),
    ]

    service = AOrderService(order_repository=repo)

    result = await service.get_orders()

    assert len(result) == 2
    repo.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_order_service_delete_order_by_id_success() -> None:
    from services.a_order_service import AOrderService

    repo = AsyncMock()
    repo.db_delete_order_by_id.return_value = True

    service = AOrderService(order_repository=repo)

    result = await service.delete_order_by_id(order_id=1)

    assert result is True
    repo.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_order_service_delete_order_by_id_not_found() -> None:
    from services.a_order_service import AOrderService

    repo = AsyncMock()
    repo.db_delete_order_by_id.return_value = False

    service = AOrderService(order_repository=repo)

    with pytest.raises(NotFoundError):
        await service.delete_order_by_id(order_id=1)

    repo.session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_order_service_create_order_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from database.schemas import OrderCreate
    from services.a_order_service import AOrderService

    repo = AsyncMock()
    repo.db_create_order.return_value = SimpleNamespace(
        id=1,
        user_id=2,
        total=Decimal("10.50"),
        created_at="2026-01-01T00:00:00",
    )

    response = AsyncMock()
    response.status_code = 200

    client = AsyncMock()
    client.get.return_value = response

    class DummyAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return client

        async def __aexit__(self, exc_type, exc, tb):
            return None

    monkeypatch.setattr("services.a_order_service.httpx.AsyncClient", DummyAsyncClient)

    service = AOrderService(order_repository=repo)

    result = await service.create_order(
        new_order=OrderCreate(user_id=2, total=Decimal("10.50")),
        service_access_token="service-token",
    )

    assert result.id == 1
    repo.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_order_service_create_order_without_user_id() -> None:
    from database.schemas import OrderCreate
    from services.a_order_service import AOrderService

    repo = AsyncMock()
    service = AOrderService(order_repository=repo)

    with pytest.raises(ValidationServiceError):
        await service.create_order(
            new_order=OrderCreate(user_id=None, total=Decimal("10.50")),
            service_access_token="service-token",
        )

    repo.session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_order_service_create_order_user_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from database.schemas import OrderCreate
    from services.a_order_service import AOrderService

    repo = AsyncMock()

    response = AsyncMock()
    response.status_code = 404

    client = AsyncMock()
    client.get.return_value = response

    class DummyAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return client

        async def __aexit__(self, exc_type, exc, tb):
            return None

    monkeypatch.setattr("services.a_order_service.httpx.AsyncClient", DummyAsyncClient)

    service = AOrderService(order_repository=repo)

    with pytest.raises(NotFoundError):
        await service.create_order(
            new_order=OrderCreate(user_id=2, total=Decimal("10.50")),
            service_access_token="service-token",
        )

    repo.session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_order_item_service_get_order_item_by_id_success() -> None:
    from services.a_order_item_service import AOrderItemService

    order_item_repo = AsyncMock()
    order_repo = AsyncMock()
    order_item_repo.db_get_order_item_by_id.return_value = SimpleNamespace(
        id=1,
        order_id=1,
        product_id=2,
        quantity=3,
        price=Decimal("9.99"),
    )

    service = AOrderItemService(
        order_item_repository=order_item_repo,
        order_repository=order_repo,
    )

    result = await service.get_order_item_by_id(order_item_id=1)

    assert result.id == 1
    order_item_repo.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_order_item_service_get_order_items_success() -> None:
    from services.a_order_item_service import AOrderItemService

    order_item_repo = AsyncMock()
    order_repo = AsyncMock()
    order_item_repo.db_get_order_items.return_value = [
        SimpleNamespace(
            id=1,
            order_id=1,
            product_id=2,
            quantity=3,
            price=Decimal("9.99"),
        )
    ]

    service = AOrderItemService(
        order_item_repository=order_item_repo,
        order_repository=order_repo,
    )

    result = await service.get_order_items()

    assert len(result) == 1
    order_item_repo.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_order_item_service_create_order_item_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from database.schemas import OrderItemCreate
    from services.a_order_item_service import AOrderItemService

    order_item_repo = AsyncMock()
    order_repo = AsyncMock()

    order_repo.db_get_order_by_id.return_value = SimpleNamespace(id=1)
    order_item_repo.db_create_order_item.return_value = SimpleNamespace(
        id=1,
        order_id=1,
        product_id=2,
        quantity=3,
        price=Decimal("9.99"),
    )

    response = AsyncMock()
    response.status_code = 200

    client = AsyncMock()
    client.get.return_value = response

    class DummyAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return client

        async def __aexit__(self, exc_type, exc, tb):
            return None

    monkeypatch.setattr(
        "services.a_order_item_service.httpx.AsyncClient",
        DummyAsyncClient,
    )

    service = AOrderItemService(
        order_item_repository=order_item_repo,
        order_repository=order_repo,
    )

    result = await service.create_order_item(
        new_order_item=OrderItemCreate(
            order_id=1,
            product_id=2,
            quantity=3,
            price=Decimal("9.99"),
        ),
        service_access_token="service-token",
    )

    assert result.id == 1
    order_item_repo.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_order_item_service_create_order_item_order_not_found() -> None:
    from database.schemas import OrderItemCreate
    from services.a_order_item_service import AOrderItemService

    order_item_repo = AsyncMock()
    order_repo = AsyncMock()
    order_repo.db_get_order_by_id.return_value = None

    service = AOrderItemService(
        order_item_repository=order_item_repo,
        order_repository=order_repo,
    )

    with pytest.raises(NotFoundError):
        await service.create_order_item(
            new_order_item=OrderItemCreate(
                order_id=1,
                product_id=2,
                quantity=3,
                price=Decimal("9.99"),
            ),
            service_access_token="service-token",
        )

    order_item_repo.session.rollback.assert_awaited_once()


def test_order_item_create_invalid_quantity_schema() -> None:
    from database.schemas import OrderItemCreate

    with pytest.raises(ValidationError):
        OrderItemCreate(
            order_id=1,
            product_id=2,
            quantity=0,
            price=Decimal("9.99"),
        )


@pytest.mark.asyncio
async def test_main_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    import main as main_module

    gathered = {"called": False, "count": 0}

    class DummyConfig:
        def __init__(self, app: str, host: str, port: int) -> None:
            self.app = app
            self.host = host
            self.port = port

    class DummyServer:
        def __init__(self, config) -> None:
            self.config = config

        async def serve(self) -> None:
            return None

    async def fake_gather(*aws):
        gathered["called"] = True
        gathered["count"] = len(aws)
        return [None for _ in aws]

    monkeypatch.setattr(main_module, "Config", DummyConfig)
    monkeypatch.setattr(main_module, "Server", DummyServer)
    monkeypatch.setattr(main_module.asyncio, "gather", fake_gather)

    await main_module.main()

    assert gathered["called"] is True
    assert gathered["count"] == 2
