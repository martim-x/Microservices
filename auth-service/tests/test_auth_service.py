from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import bcrypt
import httpx
import jwt
import pytest
from database.schemas import (
    AccessTokenPayload,
    UserCreate,
    UserOut,
    UserWithPasswordOut,
)
from services.a_auth_service import AAuthService
from services.exceptions import (
    BadRequestError,
    ConflictError,
    ExternalServiceError,
    ExternalServiceUnavailableError,
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
def mock_auth_repository(mock_session: AsyncMock) -> AsyncMock:
    repo = AsyncMock()
    repo.session = mock_session
    return repo


@pytest.fixture
def auth_service(mock_auth_repository: AsyncMock) -> AAuthService:
    return AAuthService(auth_repository=mock_auth_repository)


def test_hash_refresh_token_is_deterministic(auth_service: AAuthService) -> None:
    token = "refresh-token"
    first = auth_service.hash_refresh_token(token)
    second = auth_service.hash_refresh_token(token)

    assert first == second
    assert first != token


def test_create_refresh_token_returns_raw_and_hash(
    auth_service: AAuthService,
) -> None:
    refresh_token, refresh_token_hash = auth_service.create_refresh_token()

    assert isinstance(refresh_token, str)
    assert isinstance(refresh_token_hash, str)
    assert refresh_token
    assert refresh_token_hash == auth_service.hash_refresh_token(refresh_token)


def test_hash_password_returns_bcrypt_hash(auth_service: AAuthService) -> None:
    password = "strongpass123"

    password_hash = auth_service.hash_password(password)

    assert password_hash != password
    assert bcrypt.checkpw(password.encode(), password_hash.encode()) is True


def test_create_and_verify_access_token(auth_service: AAuthService) -> None:
    token = auth_service.create_access_token(
        payload=AccessTokenPayload(
            user_id=1,
            name="Tim",
            email="tim@example.com",
        )
    )

    payload = auth_service.verify_access_token(token)

    assert payload is not None
    assert payload.user_id == 1
    assert payload.name == "Tim"
    assert payload.email == "tim@example.com"


def test_verify_access_token_returns_none_for_wrong_type() -> None:
    from services import a_auth_service as service_module

    token = jwt.encode(
        {
            "user_id": 1,
            "name": "Tim",
            "email": "tim@example.com",
            "type": "refresh",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        key=service_module.SECRET_KEY,
        algorithm=service_module.ALGORITHM,
    )

    assert AAuthService.verify_access_token(token) is None


def test_verify_access_token_returns_none_for_invalid_token() -> None:
    assert AAuthService.verify_access_token("bad-token") is None


def test_verify_access_token_returns_none_when_required_fields_missing() -> None:
    from services import a_auth_service as service_module

    token = jwt.encode(
        {
            "type": "access",
            "name": "Tim",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        key=service_module.SECRET_KEY,
        algorithm=service_module.ALGORITHM,
    )

    assert AAuthService.verify_access_token(token) is None


@pytest.mark.parametrize(
    "status_code,error_type",
    [
        pytest.param(400, BadRequestError, id="bad-request"),
        pytest.param(401, UnauthorizedError, id="unauthorized"),
        pytest.param(404, NotFoundError, id="not-found"),
        pytest.param(409, ConflictError, id="conflict"),
        pytest.param(422, ValidationServiceError, id="validation"),
    ],
)
def test_raise_mapped_upstream_error_known_statuses(
    status_code: int,
    error_type: type[Exception],
) -> None:
    response = httpx.Response(
        status_code=status_code,
        json={"detail": "upstream error"},
    )

    with pytest.raises(error_type, match="upstream error"):
        AAuthService._raise_mapped_upstream_error(response)


def test_raise_mapped_upstream_error_503() -> None:
    response = httpx.Response(
        status_code=503,
        json={"detail": "service unavailable"},
    )

    with pytest.raises(
        ExternalServiceUnavailableError,
        match="service unavailable",
    ):
        AAuthService._raise_mapped_upstream_error(response)


def test_raise_mapped_upstream_error_unknown_status() -> None:
    response = httpx.Response(
        status_code=500,
        json={"detail": "boom"},
    )

    with pytest.raises(ExternalServiceError, match="user-product-service вернул 500"):
        AAuthService._raise_mapped_upstream_error(response)


def test_extract_error_detail_from_plain_text() -> None:
    response = httpx.Response(
        status_code=500,
        text="plain error",
    )

    assert AAuthService._extract_error_detail(response) == "plain error"


@pytest.mark.asyncio
async def test_register_success(auth_service: AAuthService) -> None:
    expected_user = UserOut(
        id=1,
        name="Tim",
        email="tim@example.com",
        created_at=datetime(2030, 1, 1, 12, 0, 0),
    )

    mocked_method = AsyncMock(return_value=expected_user)

    with patch.object(
        auth_service,
        "_create_user_in_user_service",
        mocked_method,
    ):
        result = await auth_service.register(
            new_user=UserCreate(
                name="Tim",
                email="tim@example.com",
                password="strongpass123",
            ),
            service_access_token="service-token",
        )

    assert result == expected_user
    mocked_method.assert_awaited_once()


@pytest.mark.asyncio
async def test_login_success(
    auth_service: AAuthService,
    mock_auth_repository: AsyncMock,
) -> None:
    password = "strongpass123"
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    mocked_method = AsyncMock(
        return_value=UserWithPasswordOut(
            id=1,
            name="Tim",
            email="tim@example.com",
            password_hash=password_hash,
            created_at=datetime(2030, 1, 1, 12, 0, 0),
        )
    )

    with patch.object(
        auth_service,
        "_get_user_by_email_from_user_service",
        mocked_method,
    ):
        result = await auth_service.login(
            email="tim@example.com",
            password=password,
            service_access_token="service-token",
        )

    assert "access_token" in result
    assert "refresh_token" in result
    mocked_method.assert_awaited_once()
    mock_auth_repository.db_create_refresh_token.assert_awaited_once()
    mock_auth_repository.session.commit.assert_awaited_once()
    mock_auth_repository.session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_login_raises_unauthorized_for_wrong_password(
    auth_service: AAuthService,
    mock_auth_repository: AsyncMock,
) -> None:
    mocked_method = AsyncMock(
        return_value=UserWithPasswordOut(
            id=1,
            name="Tim",
            email="tim@example.com",
            password_hash=bcrypt.hashpw(
                "correctpass".encode(), bcrypt.gensalt()
            ).decode(),
            created_at=datetime(2030, 1, 1, 12, 0, 0),
        )
    )

    with patch.object(
        auth_service,
        "_get_user_by_email_from_user_service",
        mocked_method,
    ):
        with pytest.raises(UnauthorizedError, match="Неверный пароль"):
            await auth_service.login(
                email="tim@example.com",
                password="wrongpass123",
                service_access_token="service-token",
            )

    mocked_method.assert_awaited_once()
    mock_auth_repository.session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_login_raises_unauthorized_when_name_missing(
    auth_service: AAuthService,
    mock_auth_repository: AsyncMock,
) -> None:
    password = "strongpass123"

    user_without_name = SimpleNamespace(
        id=1,
        name=None,
        email="tim@example.com",
        password_hash=bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
    )
    mocked_method = AsyncMock(return_value=user_without_name)

    with patch.object(
        auth_service,
        "_get_user_by_email_from_user_service",
        mocked_method,
    ):
        with pytest.raises(UnauthorizedError, match="Имя пользователя отсутствует"):
            await auth_service.login(
                email="tim@example.com",
                password=password,
                service_access_token="service-token",
            )

    mocked_method.assert_awaited_once()
    mock_auth_repository.session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_refresh_success(
    auth_service: AAuthService,
    mock_auth_repository: AsyncMock,
) -> None:
    refresh_token, refresh_token_hash = auth_service.create_refresh_token()

    token_record = SimpleNamespace(
        user_id=1,
        is_revoked=False,
        expires_at=datetime.now(UTC) + timedelta(days=1),
        user=SimpleNamespace(name="Tim", email="tim@example.com"),
    )

    mock_auth_repository.db_get_refresh_token.return_value = token_record

    result = await auth_service.refresh(refresh_token=refresh_token)

    assert "access_token" in result
    assert "refresh_token" in result
    mock_auth_repository.db_get_refresh_token.assert_awaited_once_with(
        refresh_token_hash=refresh_token_hash,
    )
    mock_auth_repository.db_revoke_refresh_token.assert_awaited_once_with(
        refresh_token_hash=refresh_token_hash,
    )
    mock_auth_repository.db_create_refresh_token.assert_awaited_once()
    mock_auth_repository.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_refresh_raises_for_missing_token_record(
    auth_service: AAuthService,
    mock_auth_repository: AsyncMock,
) -> None:
    mock_auth_repository.db_get_refresh_token.return_value = None

    with pytest.raises(UnauthorizedError, match="Refresh-токен недействителен"):
        await auth_service.refresh(refresh_token="bad-refresh")

    mock_auth_repository.session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_refresh_raises_for_expired_token(
    auth_service: AAuthService,
    mock_auth_repository: AsyncMock,
) -> None:
    mock_auth_repository.db_get_refresh_token.return_value = SimpleNamespace(
        user_id=1,
        is_revoked=False,
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
        user=SimpleNamespace(name="Tim", email="tim@example.com"),
    )

    with pytest.raises(UnauthorizedError, match="Refresh-токен истёк"):
        await auth_service.refresh(refresh_token="expired-refresh")

    mock_auth_repository.session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_refresh_raises_when_user_name_missing(
    auth_service: AAuthService,
    mock_auth_repository: AsyncMock,
) -> None:
    mock_auth_repository.db_get_refresh_token.return_value = SimpleNamespace(
        user_id=1,
        is_revoked=False,
        expires_at=datetime.now(UTC) + timedelta(days=1),
        user=SimpleNamespace(name=None, email="tim@example.com"),
    )

    with pytest.raises(UnauthorizedError, match="Имя пользователя отсутствует"):
        await auth_service.refresh(refresh_token="refresh-token")

    mock_auth_repository.session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_logout_success_returns_true(
    auth_service: AAuthService,
    mock_auth_repository: AsyncMock,
) -> None:
    mock_auth_repository.db_revoke_refresh_token.return_value = True

    result = await auth_service.logout(refresh_token="refresh-token")

    assert result is True
    mock_auth_repository.db_revoke_refresh_token.assert_awaited_once()
    mock_auth_repository.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_logout_rolls_back_on_error(
    auth_service: AAuthService,
    mock_auth_repository: AsyncMock,
) -> None:
    mock_auth_repository.db_revoke_refresh_token.side_effect = RuntimeError("db error")

    with pytest.raises(RuntimeError, match="db error"):
        await auth_service.logout(refresh_token="refresh-token")

    mock_auth_repository.session.rollback.assert_awaited_once()
