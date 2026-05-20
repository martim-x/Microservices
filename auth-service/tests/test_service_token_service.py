import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import jwt
import pytest
from database.schemas import ServiceAccessTokenPayload, ServiceTokenCreate
from services.a_service_token_service import AServiceTokenService
from services.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationServiceError,
)


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_service_token_repository(mock_session: AsyncMock) -> AsyncMock:
    repo = AsyncMock()
    repo.session = mock_session
    return repo


@pytest.fixture
def service_token_service(
    mock_service_token_repository: AsyncMock,
) -> AServiceTokenService:
    return AServiceTokenService(
        service_token_repository=mock_service_token_repository,
    )


def test_hash_service_secret_is_deterministic(
    service_token_service: AServiceTokenService,
) -> None:
    secret = "service-secret"
    first = service_token_service.hash_service_secret(secret)
    second = service_token_service.hash_service_secret(secret)

    assert first == second
    assert first != secret


def test_generate_service_secret_returns_non_empty_string(
    service_token_service: AServiceTokenService,
) -> None:
    secret = service_token_service.generate_service_secret()

    assert isinstance(secret, str)
    assert secret


def test_deserialize_scopes_success() -> None:
    scopes = AServiceTokenService._deserialize_scopes('["read", "write"]')

    assert scopes == ["read", "write"]


def test_deserialize_scopes_invalid_json() -> None:
    with pytest.raises(
        ValidationServiceError,
        match="allowed_scopes содержит невалидный JSON",
    ):
        AServiceTokenService._deserialize_scopes("not-json")


def test_deserialize_scopes_invalid_structure() -> None:
    with pytest.raises(
        ValidationServiceError,
        match="allowed_scopes должен быть list\\[str\\]",
    ):
        AServiceTokenService._deserialize_scopes('{"scope": "read"}')


@pytest.mark.asyncio
async def test_register_service_success(
    service_token_service: AServiceTokenService,
    mock_service_token_repository: AsyncMock,
) -> None:
    mock_service_token_repository.db_get_service_token_by_name.return_value = None
    mock_service_token_repository.db_create_service_token.return_value = (
        SimpleNamespace(
            id=1,
            service_name="auth-service",
            allowed_audience="user-product-service",
            allowed_scopes=json.dumps(["users.read", "users.create"]),
            is_active=True,
            created_at=datetime(2030, 1, 1, 12, 0, 0),
        )
    )

    result = await service_token_service.register_service(
        new_service=ServiceTokenCreate(
            service_name="auth-service",
            service_secret="x" * 16,
            allowed_audience="user-product-service",
            allowed_scopes=["users.read", "users.create"],
        )
    )

    assert result.id == 1
    assert result.service_name == "auth-service"
    assert result.allowed_scopes == ["users.read", "users.create"]
    mock_service_token_repository.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_register_service_conflict(
    service_token_service: AServiceTokenService,
    mock_service_token_repository: AsyncMock,
) -> None:
    mock_service_token_repository.db_get_service_token_by_name.return_value = object()

    with pytest.raises(ConflictError, match="Сервис с таким именем уже существует"):
        await service_token_service.register_service(
            new_service=ServiceTokenCreate(
                service_name="auth-service",
                service_secret="x" * 16,
                allowed_audience="user-product-service",
                allowed_scopes=["users.read"],
            )
        )


@pytest.mark.asyncio
async def test_issue_service_access_token_success(
    service_token_service: AServiceTokenService,
    mock_service_token_repository: AsyncMock,
) -> None:
    secret = "x" * 16
    mock_service_token_repository.db_get_service_token_by_name.return_value = (
        SimpleNamespace(
            service_name="auth-service",
            service_secret_hash=service_token_service.hash_service_secret(secret),
            allowed_audience="user-product-service",
            allowed_scopes='["users.read", "users.create"]',
            is_active=True,
        )
    )

    token = await service_token_service.issue_service_access_token(
        service_name="auth-service",
        service_secret=secret,
        audience="user-product-service",
    )

    assert isinstance(token, str)
    payload = AServiceTokenService.verify_service_access_token(
        service_access_token=token,
        expected_audience="user-product-service",
    )
    assert payload.sub == "auth-service"
    assert payload.aud == "user-product-service"
    assert payload.scope == ["users.read", "users.create"]
    assert payload.type == "service_access"


@pytest.mark.asyncio
async def test_issue_service_access_token_not_found(
    service_token_service: AServiceTokenService,
    mock_service_token_repository: AsyncMock,
) -> None:
    mock_service_token_repository.db_get_service_token_by_name.return_value = None

    with pytest.raises(NotFoundError, match="Сервис недоступен"):
        await service_token_service.issue_service_access_token(
            service_name="auth-service",
            service_secret="x" * 16,
            audience="user-product-service",
        )


@pytest.mark.asyncio
async def test_issue_service_access_token_inactive_service(
    service_token_service: AServiceTokenService,
    mock_service_token_repository: AsyncMock,
) -> None:
    mock_service_token_repository.db_get_service_token_by_name.return_value = (
        SimpleNamespace(is_active=False)
    )

    with pytest.raises(NotFoundError, match="Сервис недоступен"):
        await service_token_service.issue_service_access_token(
            service_name="auth-service",
            service_secret="x" * 16,
            audience="user-product-service",
        )


@pytest.mark.asyncio
async def test_issue_service_access_token_bad_secret(
    service_token_service: AServiceTokenService,
    mock_service_token_repository: AsyncMock,
) -> None:
    mock_service_token_repository.db_get_service_token_by_name.return_value = (
        SimpleNamespace(
            service_name="auth-service",
            service_secret_hash=service_token_service.hash_service_secret(
                "another-secret"
            ),
            allowed_audience="user-product-service",
            allowed_scopes='["users.read"]',
            is_active=True,
        )
    )

    with pytest.raises(UnauthorizedError, match="Неверные service credentials"):
        await service_token_service.issue_service_access_token(
            service_name="auth-service",
            service_secret="x" * 16,
            audience="user-product-service",
        )


@pytest.mark.asyncio
async def test_issue_service_access_token_forbidden_audience(
    service_token_service: AServiceTokenService,
    mock_service_token_repository: AsyncMock,
) -> None:
    secret = "x" * 16
    mock_service_token_repository.db_get_service_token_by_name.return_value = (
        SimpleNamespace(
            service_name="auth-service",
            service_secret_hash=service_token_service.hash_service_secret(secret),
            allowed_audience="another-service",
            allowed_scopes='["users.read"]',
            is_active=True,
        )
    )

    with pytest.raises(ForbiddenError, match="Недопустимый audience"):
        await service_token_service.issue_service_access_token(
            service_name="auth-service",
            service_secret=secret,
            audience="user-product-service",
        )


def test_verify_service_access_token_empty_token() -> None:
    with pytest.raises(UnauthorizedError, match="Пустой service access token"):
        AServiceTokenService.verify_service_access_token(
            service_access_token="",
            expected_audience="user-product-service",
        )


def test_verify_service_access_token_invalid_token() -> None:
    with pytest.raises(UnauthorizedError, match="Невалидный service access token"):
        AServiceTokenService.verify_service_access_token(
            service_access_token="bad-token",
            expected_audience="user-product-service",
        )


def test_verify_service_access_token_wrong_type() -> None:
    from services import a_service_token_service as service_module

    token = jwt.encode(
        {
            "sub": "auth-service",
            "aud": "user-product-service",
            "scope": ["users.read"],
            "type": "access",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        key=service_module.SERVICE_SECRET_KEY,
        algorithm=service_module.ALGORITHM,
    )

    with pytest.raises(UnauthorizedError, match="Неверный type токена"):
        AServiceTokenService.verify_service_access_token(
            service_access_token=token,
            expected_audience="user-product-service",
        )


def test_verify_service_access_token_missing_sub() -> None:
    from services import a_service_token_service as service_module

    token = jwt.encode(
        {
            "aud": "user-product-service",
            "scope": ["users.read"],
            "type": "service_access",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        key=service_module.SERVICE_SECRET_KEY,
        algorithm=service_module.ALGORITHM,
    )

    with pytest.raises(UnauthorizedError, match="Отсутствует sub"):
        AServiceTokenService.verify_service_access_token(
            service_access_token=token,
            expected_audience="user-product-service",
        )


def test_verify_service_access_token_invalid_scope() -> None:
    from services import a_service_token_service as service_module

    token = jwt.encode(
        {
            "sub": "auth-service",
            "aud": "user-product-service",
            "scope": "users.read",
            "type": "service_access",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        key=service_module.SERVICE_SECRET_KEY,
        algorithm=service_module.ALGORITHM,
    )

    with pytest.raises(UnauthorizedError, match="Некорректный scope"):
        AServiceTokenService.verify_service_access_token(
            service_access_token=token,
            expected_audience="user-product-service",
        )


def test_require_scope_success() -> None:
    payload = ServiceAccessTokenPayload(
        sub="auth-service",
        aud="user-product-service",
        scope=["users.read", "users.create"],
        type="service_access",
    )

    AServiceTokenService.require_scope(
        service_access_token_payload=payload,
        required_scope="users.read",
    )


def test_require_scope_forbidden() -> None:
    payload = ServiceAccessTokenPayload(
        sub="auth-service",
        aud="user-product-service",
        scope=["users.read"],
        type="service_access",
    )

    with pytest.raises(ForbiddenError, match="Недостаточно прав у сервиса"):
        AServiceTokenService.require_scope(
            service_access_token_payload=payload,
            required_scope="users.create",
        )
