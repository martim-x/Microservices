from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from services.exceptions import ServiceError


def test_app_metadata() -> None:
    from api.app import app
    from api.settings import settings

    assert app.title == settings.USER_PRODUCT_SERVICE_NAME
    assert app.version == settings.USER_PRODUCT_SERVICE_VERSION


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

    repo_instance = AsyncMock()
    repo_instance.db_get_service_token_by_name.return_value = None

    service_instance = AsyncMock()
    service_instance.register_service = AsyncMock()

    class DummySession:
        async def __aenter__(self):
            return AsyncMock()

        async def __aexit__(self, exc_type, exc, tb):
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
        assert list(checks.values())[0]["ok"] is True
        assert app.state.redis_client is redis_client

    assert app.state.services["health"]["shutdown_requested"] is True
    redis_client.close.assert_awaited_once()


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
