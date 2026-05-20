from unittest.mock import AsyncMock, Mock

import pytest
from api.auth.core import auth_router
from api.dependencies.services import (
    get_auth_service,
    get_service_token_service,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def mock_auth_service() -> AsyncMock:
    service = AsyncMock()
    service.verify_access_token = Mock()
    return service


@pytest.fixture
def mock_service_token_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def app(
    mock_auth_service: AsyncMock,
    mock_service_token_service: AsyncMock,
) -> FastAPI:
    app = FastAPI()

    app.include_router(auth_router)

    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
    app.dependency_overrides[get_service_token_service] = (
        lambda: mock_service_token_service
    )

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def test_register_success(
    client: TestClient,
    mock_auth_service: AsyncMock,
    mock_service_token_service: AsyncMock,
) -> None:
    mock_service_token_service.issue_service_access_token.return_value = "service-token"
    mock_auth_service.register.return_value = {
        "id": 1,
        "name": "Tim",
        "email": "tim@example.com",
        "created_at": "2026-05-20T20:00:00",
    }

    response = client.post(
        "/api/auth/register",
        json={
            "name": "Tim",
            "email": "tim@example.com",
            "password": "strongpass123",
        },
    )

    assert response.status_code == 201
    assert response.json()["id"] == 1
    assert response.json()["name"] == "Tim"
    assert response.json()["email"] == "tim@example.com"

    mock_service_token_service.issue_service_access_token.assert_awaited_once()
    mock_auth_service.register.assert_awaited_once()


def test_register_validation_error(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "name": "",
            "email": "bad-email",
            "password": "123",
        },
    )

    assert response.status_code == 422


def test_login_success(
    client: TestClient,
    mock_auth_service: AsyncMock,
    mock_service_token_service: AsyncMock,
) -> None:
    mock_service_token_service.issue_service_access_token.return_value = "service-token"
    mock_auth_service.login.return_value = {
        "access_token": "access-123",
        "refresh_token": "refresh-123",
    }

    response = client.post(
        "/api/auth/login",
        json={
            "email": "tim@example.com",
            "password": "strongpass123",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "access-123",
        "token_type": "bearer",
    }

    set_cookie = response.headers.get("set-cookie", "")
    assert "refresh_token=refresh-123" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie

    mock_service_token_service.issue_service_access_token.assert_awaited_once()
    mock_auth_service.login.assert_awaited_once_with(
        email="tim@example.com",
        password="strongpass123",
        service_access_token="service-token",
    )


@pytest.mark.parametrize(
    "email,password",
    [
        pytest.param("bad-email", "strongpass123", id="invalid-email"),
        pytest.param("tim@example.com", "short", id="short-password"),
    ],
)
def test_login_validation_error(
    client: TestClient,
    email: str,
    password: str,
) -> None:
    response = client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 422


def test_refresh_success(
    client: TestClient,
    mock_auth_service: AsyncMock,
) -> None:
    mock_auth_service.refresh.return_value = {
        "access_token": "new-access",
        "refresh_token": "new-refresh",
    }

    client.cookies.set("refresh_token", "old-refresh")
    response = client.post("/api/auth/refresh")

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "new-access",
        "token_type": "bearer",
    }

    set_cookie = response.headers.get("set-cookie", "")
    assert "refresh_token=new-refresh" in set_cookie
    assert "HttpOnly" in set_cookie

    mock_auth_service.refresh.assert_awaited_once_with(
        refresh_token="old-refresh",
    )


def test_refresh_without_cookie_returns_unauthorized(
    client: TestClient,
    mock_auth_service: AsyncMock,
) -> None:
    response = client.post("/api/auth/refresh")

    assert response.status_code == 500
    mock_auth_service.refresh.assert_not_called()


def test_logout_with_cookie(
    client: TestClient,
    mock_auth_service: AsyncMock,
) -> None:
    client.cookies.set("refresh_token", "refresh-123")
    response = client.post("/api/auth/logout")

    assert response.status_code == 204

    set_cookie = response.headers.get("set-cookie", "")
    assert "refresh_token=" in set_cookie

    mock_auth_service.logout.assert_awaited_once_with(
        refresh_token="refresh-123",
    )


def test_logout_without_cookie(
    client: TestClient,
    mock_auth_service: AsyncMock,
) -> None:
    response = client.post("/api/auth/logout")

    assert response.status_code == 204
    mock_auth_service.logout.assert_not_called()


def test_verify_success(
    client: TestClient,
    mock_auth_service: AsyncMock,
) -> None:
    mock_auth_service.verify_access_token.return_value = {
        "user_id": 1,
        "name": "Tim",
        "email": "tim@example.com",
    }

    response = client.get("/api/auth/verify/token-123")

    assert response.status_code == 200
    assert response.json() == {
        "user_id": 1,
        "name": "Tim",
        "email": "tim@example.com",
    }

    mock_auth_service.verify_access_token.assert_called_once_with("token-123")


def test_verify_invalid_token(
    client: TestClient,
    mock_auth_service: AsyncMock,
) -> None:
    mock_auth_service.verify_access_token.return_value = None

    response = client.get("/api/auth/verify/bad-token")

    assert response.status_code == 500
    mock_auth_service.verify_access_token.assert_called_once_with("bad-token")
