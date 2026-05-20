from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from services.exceptions import ServiceError


def test_app_metadata() -> None:
    from api.app import app
    from api.settings import settings

    assert app.title == settings.REPORT_SERVICE_NAME
    assert app.version == settings.REPORT_SERVICE_VERSION


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

    connection = AsyncMock()
    channel = AsyncMock()
    connection.channel.return_value = channel
    channel.is_closed = False
    connection.is_closed = False

    async def fake_connect_robust(url: str):
        return connection

    service_instance = AsyncMock()
    service_instance.start = AsyncMock()
    service_instance.stop = AsyncMock()

    monkeypatch.setattr(
        app_module.aio_pika,
        "connect_robust",
        fake_connect_robust,
    )
    monkeypatch.setattr(
        app_module,
        "AMessageQueueService",
        lambda **kwargs: service_instance,
    )

    async with app_module.lifespan(app):
        health = app.state.services["health"]
        assert health["startup_complete"] is True
        assert health["shutdown_requested"] is False
        assert list(health["checks"].values())[0]["ok"] is True

        assert app.state.rabbitmq_connection is connection
        assert app.state.rabbitmq_channel is channel
        assert app.state.message_queue_service is service_instance

    assert app.state.services["health"]["shutdown_requested"] is True
    channel.set_qos.assert_awaited_once_with(prefetch_count=1)
    service_instance.start.assert_awaited_once()
    service_instance.stop.assert_awaited_once()
    channel.close.assert_awaited_once()
    connection.close.assert_awaited_once()


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
    assert gathered["count"] == 1
