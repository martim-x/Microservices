from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, Mock, create_autospec

import pytest
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from redis.asyncio import Redis
from repository.a_order_item_repository import AOrderItemRepository
from repository.a_order_repository import AOrderRepository
from repository.a_service_token_repository import AServiceTokenRepository
from services.a_message_queue_service import AMessageQueueService
from services.a_order_item_service import AOrderItemService
from services.a_order_service import AOrderService
from services.a_service_token_service import AServiceTokenService
from services.cache.a_order_cache_service import AOrderCacheService
from services.cache.a_order_item_cache_service import AOrderItemCacheService


@pytest.mark.asyncio
async def test_get_service_token_repository() -> None:
    from api.dependencies.repositories import get_service_token_repository

    session = cast(Any, object())
    repo = await get_service_token_repository(session=session)

    assert isinstance(repo, AServiceTokenRepository)
    assert repo.session is session


@pytest.mark.asyncio
async def test_get_order_read_repository() -> None:
    from api.dependencies.repositories import get_order_read_repository

    session = cast(Any, object())
    repo = await get_order_read_repository(session=session)

    assert isinstance(repo, AOrderRepository)
    assert repo.session is session


@pytest.mark.asyncio
async def test_get_order_write_repository() -> None:
    from api.dependencies.repositories import get_order_write_repository

    session = cast(Any, object())
    repo = await get_order_write_repository(session=session)

    assert isinstance(repo, AOrderRepository)
    assert repo.session is session


@pytest.mark.asyncio
async def test_get_order_item_read_repository() -> None:
    from api.dependencies.repositories import get_order_item_read_repository

    session = cast(Any, object())
    repo = await get_order_item_read_repository(session=session)

    assert isinstance(repo, AOrderItemRepository)
    assert repo.session is session


@pytest.mark.asyncio
async def test_get_order_item_write_repository() -> None:
    from api.dependencies.repositories import get_order_item_write_repository

    session = cast(Any, object())
    repo = await get_order_item_write_repository(session=session)

    assert isinstance(repo, AOrderItemRepository)
    assert repo.session is session


@pytest.mark.asyncio
async def test_get_service_token_service() -> None:
    from api.dependencies.services import get_service_token_service

    repo = create_autospec(AServiceTokenRepository, instance=True)
    service = await get_service_token_service(service_token_repository=repo)

    assert isinstance(service, AServiceTokenService)
    assert service.service_token_repository is repo


@pytest.mark.asyncio
async def test_get_order_read_service() -> None:
    from api.dependencies.services import get_order_read_service

    repo = create_autospec(AOrderRepository, instance=True)
    service = await get_order_read_service(order_repo=repo)

    assert isinstance(service, AOrderService)
    assert service.order_repository is repo


@pytest.mark.asyncio
async def test_get_order_write_service() -> None:
    from api.dependencies.services import get_order_write_service

    repo = create_autospec(AOrderRepository, instance=True)
    service = await get_order_write_service(order_repo=repo)

    assert isinstance(service, AOrderService)
    assert service.order_repository is repo


@pytest.mark.asyncio
async def test_get_order_item_read_service() -> None:
    from api.dependencies.services import get_order_item_read_service

    order_repo = create_autospec(AOrderRepository, instance=True)
    order_item_repo = create_autospec(AOrderItemRepository, instance=True)

    service = await get_order_item_read_service(
        order_item_repo=order_item_repo,
        order_repo=order_repo,
    )

    assert isinstance(service, AOrderItemService)
    assert service.order_item_repository is order_item_repo
    assert service.order_repository is order_repo


@pytest.mark.asyncio
async def test_get_order_item_write_service() -> None:
    from api.dependencies.services import get_order_item_write_service

    order_repo = create_autospec(AOrderRepository, instance=True)
    order_item_repo = create_autospec(AOrderItemRepository, instance=True)

    service = await get_order_item_write_service(
        order_item_repo=order_item_repo,
        order_repo=order_repo,
    )

    assert isinstance(service, AOrderItemService)
    assert service.order_item_repository is order_item_repo
    assert service.order_repository is order_repo


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
async def test_get_order_cache_service() -> None:
    from api.dependencies.services import get_order_cache_service

    redis_client = cast(Redis, AsyncMock(spec=Redis))
    order_repo = create_autospec(AOrderRepository, instance=True)
    order_service = AOrderService(order_repository=order_repo)

    cache_service = await get_order_cache_service(
        redis_client=redis_client,
        order_service=order_service,
    )

    assert isinstance(cache_service, AOrderCacheService)
    assert cache_service.redis is redis_client
    assert cache_service.order_service is order_service


@pytest.mark.asyncio
async def test_get_order_item_cache_service() -> None:
    from api.dependencies.services import get_order_item_cache_service

    redis_client = cast(Redis, AsyncMock(spec=Redis))
    order_item_repo = create_autospec(AOrderItemRepository, instance=True)
    order_repo = create_autospec(AOrderRepository, instance=True)
    order_item_service = AOrderItemService(
        order_item_repository=order_item_repo,
        order_repository=order_repo,
    )

    cache_service = await get_order_item_cache_service(
        redis_client=redis_client,
        order_item_service=order_item_service,
    )

    assert isinstance(cache_service, AOrderItemCacheService)
    assert cache_service.redis is redis_client
    assert cache_service.order_item_service is order_item_service


def test_get_message_queue_service() -> None:
    from api.dependencies.services import get_message_queue_service

    mq_service = AMessageQueueService(
        channel=cast(Any, object()),
        routing_key="test.route",
    )

    app = type("App", (), {})()
    app.state = type("State", (), {})()
    app.state.message_queue_service = mq_service

    request = Request(
        {
            "type": "http",
            "headers": [],
            "app": app,
        }
    )

    result = get_message_queue_service(request=request)

    assert result is mq_service


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
async def test_get_current_user_success(monkeypatch: pytest.MonkeyPatch) -> None:
    from api.dependencies.security import get_current_user

    class DummyResponse:
        status_code = 200

        def json(self) -> dict[str, object]:
            return {"whatever": "payload"}

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

    validated = SimpleNamespace(user_id=1, name="Tim", email="tim@example.com")

    monkeypatch.setattr(
        "api.dependencies.security.httpx.AsyncClient",
        DummyAsyncClient,
    )
    monkeypatch.setattr(
        "api.dependencies.security.AccessTokenPayload",
        SimpleNamespace(model_validate=lambda data: validated),
    )

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="access-token",
    )

    result = await get_current_user(credentials=credentials)

    assert result.user_id == 1
    assert result.name == "Tim"
    assert result.email == "tim@example.com"
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
