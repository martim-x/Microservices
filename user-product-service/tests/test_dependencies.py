from typing import Any, cast
from unittest.mock import AsyncMock, Mock, create_autospec

import pytest
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from redis.asyncio import Redis
from repository.a_product_repository import AProductRepository
from repository.a_service_token_repository import AServiceTokenRepository
from repository.a_user_repository import AUserRepository
from services.a_exchange_service import AExchangeService
from services.a_product_service import AProductService
from services.a_service_token_service import AServiceTokenService
from services.a_user_service import AUserService
from services.cache.a_product_cache_service import AProductCacheService
from services.cache.a_user_cache_service import AUserCacheService


@pytest.mark.asyncio
async def test_get_service_token_repository() -> None:
    from api.dependencies.repositories import get_service_token_repository

    session = cast(Any, object())
    repo = await get_service_token_repository(session=session)

    assert isinstance(repo, AServiceTokenRepository)
    assert repo.session is session


@pytest.mark.asyncio
async def test_get_user_read_repository() -> None:
    from api.dependencies.repositories import get_user_read_repository

    session = cast(Any, object())
    repo = await get_user_read_repository(session=session)

    assert isinstance(repo, AUserRepository)
    assert repo.session is session


@pytest.mark.asyncio
async def test_get_user_write_repository() -> None:
    from api.dependencies.repositories import get_user_write_repository

    session = cast(Any, object())
    repo = await get_user_write_repository(session=session)

    assert isinstance(repo, AUserRepository)
    assert repo.session is session


@pytest.mark.asyncio
async def test_get_product_read_repository() -> None:
    from api.dependencies.repositories import get_product_read_repository

    session = cast(Any, object())
    repo = await get_product_read_repository(session=session)

    assert isinstance(repo, AProductRepository)
    assert repo.session is session


@pytest.mark.asyncio
async def test_get_product_write_repository() -> None:
    from api.dependencies.repositories import get_product_write_repository

    session = cast(Any, object())
    repo = await get_product_write_repository(session=session)

    assert isinstance(repo, AProductRepository)
    assert repo.session is session


@pytest.mark.asyncio
async def test_get_service_token_service() -> None:
    from api.dependencies.services import get_service_token_service

    repo = create_autospec(AServiceTokenRepository, instance=True)
    service = await get_service_token_service(service_token_repository=repo)

    assert isinstance(service, AServiceTokenService)
    assert service.service_token_repository is repo


@pytest.mark.asyncio
async def test_get_user_read_service() -> None:
    from api.dependencies.services import get_user_read_service

    repo = create_autospec(AUserRepository, instance=True)
    service = await get_user_read_service(user_repo=repo)

    assert isinstance(service, AUserService)
    assert service.user_repository is repo


@pytest.mark.asyncio
async def test_get_user_write_service() -> None:
    from api.dependencies.services import get_user_write_service

    repo = create_autospec(AUserRepository, instance=True)
    service = await get_user_write_service(user_repo=repo)

    assert isinstance(service, AUserService)
    assert service.user_repository is repo


@pytest.mark.asyncio
async def test_get_product_read_service() -> None:
    from api.dependencies.services import get_product_read_service

    repo = create_autospec(AProductRepository, instance=True)
    service = await get_product_read_service(product_repo=repo)

    assert isinstance(service, AProductService)
    assert service.product_repository is repo


@pytest.mark.asyncio
async def test_get_product_write_service() -> None:
    from api.dependencies.services import get_product_write_service

    repo = create_autospec(AProductRepository, instance=True)
    service = await get_product_write_service(product_repo=repo)

    assert isinstance(service, AProductService)
    assert service.product_repository is repo


@pytest.mark.asyncio
async def test_get_redis_client() -> None:
    from api.dependencies.services import get_redis_client

    redis_client = cast(Redis, AsyncMock(spec=Redis))

    app = type("App", (), {})()
    app.state = type("State", (), {})()
    app.state.redis_client = redis_client

    request = Request(
        {
            "type": "http",
            "headers": [],
            "app": app,
        }
    )

    result = await get_redis_client(request=request)

    assert result is redis_client


@pytest.mark.asyncio
async def test_get_user_cache_service() -> None:
    from api.dependencies.services import get_user_cache_service

    redis_client = cast(Redis, AsyncMock(spec=Redis))
    user_repo = create_autospec(AUserRepository, instance=True)
    user_service = AUserService(user_repository=user_repo)

    cache_service = await get_user_cache_service(
        redis_client=redis_client,
        user_service=user_service,
    )

    assert isinstance(cache_service, AUserCacheService)
    assert cache_service.redis is redis_client
    assert cache_service.user_service is user_service


@pytest.mark.asyncio
async def test_get_product_cache_service() -> None:
    from api.dependencies.services import get_product_cache_service

    redis_client = cast(Redis, AsyncMock(spec=Redis))
    product_repo = create_autospec(AProductRepository, instance=True)
    product_service = AProductService(product_repository=product_repo)

    cache_service = await get_product_cache_service(
        redis_client=redis_client,
        product_service=product_service,
    )

    assert isinstance(cache_service, AProductCacheService)
    assert cache_service.redis is redis_client
    assert cache_service.product_service is product_service


@pytest.mark.asyncio
async def test_get_exchange_service() -> None:
    from api.dependencies.services import get_exchange_service

    service = await get_exchange_service()

    assert isinstance(service, AExchangeService)


@pytest.mark.asyncio
async def test_get_current_service_unauthorized() -> None:
    from api.dependencies.security import get_current_service

    service_token_service = Mock()
    service_token_service.verify_service_access_token.return_value = None

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="bad-token",
    )

    with pytest.raises(HTTPException) as exc:
        await get_current_service(
            credentials=credentials,
            service_token_service=service_token_service,
        )

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_service_success() -> None:
    from api.dependencies.security import get_current_service

    token_payload = {"sub": "svc"}
    service_token_service = Mock()
    service_token_service.verify_service_access_token.return_value = token_payload

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="good-token",
    )

    result = await get_current_service(
        credentials=credentials,
        service_token_service=service_token_service,
    )

    assert result == token_payload


@pytest.mark.asyncio
async def test_get_current_user_success(monkeypatch: pytest.MonkeyPatch) -> None:
    from api.dependencies.security import get_current_user

    class DummyResponse:
        status_code = 200

        def json(self) -> dict[str, object]:
            return {
                "id": 1,
                "email": "tim@example.com",
                "name": "Tim",
            }

    client = AsyncMock()
    client.get.return_value = DummyResponse()

    class DummyAsyncClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> AsyncMock:
            return client

        async def __aexit__(
            self,
            exc_type: object,
            exc: object,
            tb: object,
        ) -> None:
            return None

    validated = object()

    class DummyAccessTokenPayload:
        @staticmethod
        def model_validate(data: dict[str, object]) -> object:
            assert data == {
                "id": 1,
                "email": "tim@example.com",
                "name": "Tim",
            }
            return validated

    monkeypatch.setattr("api.dependencies.security.httpx.AsyncClient", DummyAsyncClient)
    monkeypatch.setattr(
        "api.dependencies.security.AccessTokenPayload",
        DummyAccessTokenPayload,
    )

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="access-token",
    )

    result = await get_current_user(credentials=credentials)

    assert result is validated
    client.get.assert_awaited_once_with("/auth/verify/access-token")


@pytest.mark.asyncio
async def test_get_current_user_401(monkeypatch: pytest.MonkeyPatch) -> None:
    from api.dependencies.security import get_current_user

    response = AsyncMock()
    response.status_code = 401

    client = AsyncMock()
    client.get.return_value = response

    class DummyAsyncClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> AsyncMock:
            return client

        async def __aexit__(
            self,
            exc_type: object,
            exc: object,
            tb: object,
        ) -> None:
            return None

    monkeypatch.setattr("api.dependencies.security.httpx.AsyncClient", DummyAsyncClient)

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="access-token",
    )

    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=credentials)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_400(monkeypatch: pytest.MonkeyPatch) -> None:
    from api.dependencies.security import get_current_user

    response = AsyncMock()
    response.status_code = 400

    client = AsyncMock()
    client.get.return_value = response

    class DummyAsyncClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> AsyncMock:
            return client

        async def __aexit__(
            self,
            exc_type: object,
            exc: object,
            tb: object,
        ) -> None:
            return None

    monkeypatch.setattr("api.dependencies.security.httpx.AsyncClient", DummyAsyncClient)

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="access-token",
    )

    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=credentials)

    assert exc.value.status_code == 401
