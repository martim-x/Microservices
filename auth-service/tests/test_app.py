from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from services.exceptions import ServiceError


def test_app_metadata() -> None:
    from api.app import app
    from api.settings import settings

    assert app.title == settings.AUTH_SERVICE_NAME
    assert app.version == settings.AUTH_SERVICE_VERSION


def test_process_time_header_middleware() -> None:
    from api.app import add_process_time_header

    app = FastAPI()

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    app.middleware("http")(add_process_time_header)

    client = TestClient(app)
    response = client.get("/ping")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert "X-Process-Time" in response.headers


def test_error_handler_returns_service_error_response() -> None:
    from api.app import error_handler

    app = FastAPI()

    @app.get("/boom")
    async def boom():
        raise ServiceError(status_code=418, detail="service boom")

    app.middleware("http")(error_handler)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom")

    assert response.status_code == 418
    assert response.json() == {"detail": "service boom"}


def test_error_handler_returns_http_exception_response() -> None:
    from api.app import error_handler

    app = FastAPI()

    @app.get("/boom")
    async def boom():
        raise HTTPException(status_code=404, detail="missing")

    app.middleware("http")(error_handler)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom")

    assert response.status_code == 404
    assert response.json() == {"detail": "missing"}


def test_error_handler_returns_internal_server_error_response() -> None:
    from api.app import error_handler

    app = FastAPI()

    @app.get("/boom")
    async def boom():
        raise RuntimeError("unexpected")

    app.middleware("http")(error_handler)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {"detail": "Внутренняя ошибка сервера"}


@pytest.mark.asyncio
async def test_lifespan_initializes_health_and_registers_service(monkeypatch) -> None:
    from api import app as app_module

    app = FastAPI()

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
        app_module, "AServiceTokenRepository", lambda session: repo_instance
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
        assert health["checks"][app_module.settings.DB_SERVICE_NAME]["ok"] is True
        assert health["checks"][app_module.settings.AUTH_SERVICE_NAME]["ok"] is True

    assert app.state.services["health"]["shutdown_requested"] is True
    repo_instance.db_get_service_token_by_name.assert_awaited_once_with(
        service_name=app_module.settings.AUTH_SERVICE_NAME,
    )
    service_instance.register_service.assert_awaited_once()


@pytest.mark.asyncio
async def test_lifespan_skips_registration_if_service_exists(monkeypatch) -> None:
    from api import app as app_module

    app = FastAPI()

    repo_instance = AsyncMock()
    repo_instance.db_get_service_token_by_name.return_value = object()

    service_instance = AsyncMock()
    service_instance.register_service = AsyncMock()

    class DummySession:
        async def __aenter__(self):
            return AsyncMock()

        async def __aexit__(self, exc_type, exc, tb):
            return None

    monkeypatch.setattr(app_module, "SessionLocalMaster", lambda: DummySession())
    monkeypatch.setattr(
        app_module, "AServiceTokenRepository", lambda session: repo_instance
    )
    monkeypatch.setattr(
        app_module,
        "AServiceTokenService",
        lambda service_token_repository: service_instance,
    )

    async with app_module.lifespan(app):
        assert app.state.services["health"]["startup_complete"] is True

    service_instance.register_service.assert_not_awaited()
