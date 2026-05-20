import datetime

import pytest
from database.schemas import (
    AccessTokenPayload,
    AuthTokenOut,
    ServiceAccessTokenPayload,
    ServiceTokenCreate,
    ServiceTokenOut,
    TokenPairResponse,
    UserCreate,
    UserLogin,
    UserOut,
    UserWithPasswordOut,
)
from pydantic import ValidationError

# ─── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_user_login() -> UserLogin:
    return UserLogin(
        email="user@example.com",
        password="strong_pass_123",
    )


@pytest.fixture
def sample_access_token_payload() -> AccessTokenPayload:
    return AccessTokenPayload(
        user_id=1,
        name="Test User",
        email="user@example.com",
    )


@pytest.fixture
def sample_token_pair_response() -> TokenPairResponse:
    return TokenPairResponse(
        access_token="jwt.token.value",
        token_type="bearer",
    )


@pytest.fixture
def sample_auth_token_out() -> AuthTokenOut:
    return AuthTokenOut(
        id=1,
        user_id=1,
        expires_at=datetime.datetime(2030, 1, 1, 12, 0, 0),
        is_revoked=False,
    )


@pytest.fixture
def sample_user_create() -> UserCreate:
    return UserCreate(
        name="Test User",
        email="user@example.com",
        password="strong_pass_123",
    )


@pytest.fixture
def sample_user_out() -> UserOut:
    return UserOut(
        id=1,
        name="Test User",
        email="user@example.com",
        created_at=datetime.datetime(2030, 1, 1, 12, 0, 0),
    )


@pytest.fixture
def sample_user_with_password_out() -> UserWithPasswordOut:
    return UserWithPasswordOut(
        id=1,
        name="Test User",
        email="user@example.com",
        password_hash="hash123",
        created_at=datetime.datetime(2030, 1, 1, 12, 0, 0),
    )


@pytest.fixture
def sample_service_token_create() -> ServiceTokenCreate:
    return ServiceTokenCreate(
        service_name="test-service",
        service_secret="x" * 16,
        allowed_audience="test-audience",
        allowed_scopes=["read", "write"],
    )


@pytest.fixture
def sample_service_token_out() -> ServiceTokenOut:
    return ServiceTokenOut(
        id=1,
        service_name="test-service",
        allowed_audience="test-audience",
        allowed_scopes=["read", "write"],
        is_active=True,
        created_at=datetime.datetime(2030, 1, 1, 12, 0, 0),
    )


@pytest.fixture
def sample_service_access_token_payload() -> ServiceAccessTokenPayload:
    return ServiceAccessTokenPayload(
        sub="test-service",
        aud="test-audience",
        scope=["read", "write"],
        type="service",
        exp=datetime.datetime(2030, 1, 1, 12, 0, 0),
    )


# ─── UserLogin ─────────────────────────────────────────────────────────────────


def test_user_login_creation(sample_user_login: UserLogin) -> None:
    assert sample_user_login.email == "user@example.com"
    assert sample_user_login.password == "strong_pass_123"


@pytest.mark.parametrize(
    "email,password",
    [
        pytest.param("invalid-email", "strong_pass_123", id="invalid-email"),
        pytest.param("user@example.com", "short", id="password-too-short"),
        pytest.param("user@example.com", "x" * 101, id="password-too-long"),
    ],
)
def test_user_login_validation_errors(email: str, password: str) -> None:
    with pytest.raises(ValidationError):
        UserLogin(email=email, password=password)


# ─── AccessTokenPayload ────────────────────────────────────────────────────────


def test_access_token_payload_creation(
    sample_access_token_payload: AccessTokenPayload,
) -> None:
    assert sample_access_token_payload.user_id == 1
    assert sample_access_token_payload.name == "Test User"
    assert sample_access_token_payload.email == "user@example.com"


@pytest.mark.parametrize(
    "user_id,name,email",
    [
        pytest.param(0, "User", "user@example.com", id="user-id-zero"),
        pytest.param(-1, "User", "user@example.com", id="user-id-negative"),
        pytest.param(1, "x" * 51, "user@example.com", id="name-too-long"),
    ],
)
def test_access_token_payload_validation_errors(
    user_id: int,
    name: str,
    email: str,
) -> None:
    with pytest.raises(ValidationError):
        AccessTokenPayload(user_id=user_id, name=name, email=email)


def test_access_token_payload_allows_plain_string_email() -> None:
    payload = AccessTokenPayload(
        user_id=1,
        name="User",
        email="invalid-email",
    )

    assert payload.email == "invalid-email"


# ─── TokenPairResponse ─────────────────────────────────────────────────────────


def test_token_pair_response_creation(
    sample_token_pair_response: TokenPairResponse,
) -> None:
    assert sample_token_pair_response.access_token == "jwt.token.value"
    assert sample_token_pair_response.token_type == "bearer"


def test_token_pair_response_allows_empty_strings() -> None:
    response = TokenPairResponse(
        access_token="",
        token_type="",
    )

    assert response.access_token == ""
    assert response.token_type == ""


# ─── AuthTokenOut ──────────────────────────────────────────────────────────────


def test_auth_token_out_creation(sample_auth_token_out: AuthTokenOut) -> None:
    assert sample_auth_token_out.id == 1
    assert sample_auth_token_out.user_id == 1
    assert sample_auth_token_out.is_revoked is False
    assert isinstance(sample_auth_token_out.expires_at, datetime.datetime)


# ─── UserCreate ────────────────────────────────────────────────────────────────


def test_user_create_creation(sample_user_create: UserCreate) -> None:
    assert sample_user_create.name == "Test User"
    assert sample_user_create.email == "user@example.com"
    assert sample_user_create.password == "strong_pass_123"


def test_user_create_name_sanitized() -> None:
    user = UserCreate(
        name="   <b>Test User</b>   ",
        email="user@example.com",
        password="strong_pass_123",
    )
    assert user.name == "&lt;b&gt;Test User&lt;/b&gt;"


@pytest.mark.parametrize(
    "name",
    [
        pytest.param("", id="empty-name"),
        pytest.param("   ", id="blank-name"),
    ],
)
def test_user_create_name_validation_errors(name: str) -> None:
    with pytest.raises(ValidationError):
        UserCreate(
            name=name,
            email="user@example.com",
            password="strong_pass_123",
        )


@pytest.mark.parametrize(
    "email",
    [
        pytest.param("invalid-email", id="invalid-email"),
        pytest.param("user@", id="email-no-domain"),
    ],
)
def test_user_create_email_validation_errors(email: str) -> None:
    with pytest.raises(ValidationError):
        UserCreate(
            name="User",
            email=email,
            password="strong_pass_123",
        )


@pytest.mark.parametrize(
    "password",
    [
        pytest.param("short", id="password-too-short"),
        pytest.param("x" * 101, id="password-too-long"),
    ],
)
def test_user_create_password_validation_errors(password: str) -> None:
    with pytest.raises(ValidationError):
        UserCreate(
            name="User",
            email="user@example.com",
            password=password,
        )


# ─── UserOut / UserWithPasswordOut ────────────────────────────────────────────


def test_user_out_creation(sample_user_out: UserOut) -> None:
    assert sample_user_out.id == 1
    assert sample_user_out.name == "Test User"
    assert sample_user_out.email == "user@example.com"
    assert isinstance(sample_user_out.created_at, datetime.datetime)


def test_user_with_password_out_creation(
    sample_user_with_password_out: UserWithPasswordOut,
) -> None:
    assert sample_user_with_password_out.id == 1
    assert sample_user_with_password_out.password_hash == "hash123"


# ─── ServiceTokenCreate ────────────────────────────────────────────────────────


def test_service_token_create_creation(
    sample_service_token_create: ServiceTokenCreate,
) -> None:
    assert sample_service_token_create.service_name == "test-service"
    assert sample_service_token_create.service_secret == "x" * 16
    assert sample_service_token_create.allowed_audience == "test-audience"
    assert sample_service_token_create.allowed_scopes == ["read", "write"]


@pytest.mark.parametrize(
    "service_name,service_secret,allowed_audience,allowed_scopes",
    [
        pytest.param(
            "",
            "x" * 16,
            "aud",
            ["read"],
            id="empty-service-name",
        ),
        pytest.param(
            "a" * 101,
            "x" * 16,
            "aud",
            ["read"],
            id="service-name-too-long",
        ),
        pytest.param(
            "service",
            "short-secret",
            "aud",
            ["read"],
            id="secret-too-short",
        ),
        pytest.param(
            "service",
            "x" * 16,
            "",
            ["read"],
            id="empty-audience",
        ),
        pytest.param(
            "service",
            "x" * 16,
            "a" * 101,
            ["read"],
            id="audience-too-long",
        ),
    ],
)
def test_service_token_create_validation_errors(
    service_name: str,
    service_secret: str,
    allowed_audience: str,
    allowed_scopes: list[str],
) -> None:
    with pytest.raises(ValidationError):
        ServiceTokenCreate(
            service_name=service_name,
            service_secret=service_secret,
            allowed_audience=allowed_audience,
            allowed_scopes=allowed_scopes,
        )


# ─── ServiceTokenOut ──────────────────────────────────────────────────────────


def test_service_token_out_creation(
    sample_service_token_out: ServiceTokenOut,
) -> None:
    assert sample_service_token_out.id == 1
    assert sample_service_token_out.service_name == "test-service"
    assert sample_service_token_out.allowed_audience == "test-audience"
    assert sample_service_token_out.allowed_scopes == ["read", "write"]
    assert sample_service_token_out.is_active is True
    assert isinstance(sample_service_token_out.created_at, datetime.datetime)


# ─── ServiceAccessTokenPayload ─────────────────────────────────────────────────


def test_service_access_token_payload_creation(
    sample_service_access_token_payload: ServiceAccessTokenPayload,
) -> None:
    assert sample_service_access_token_payload.sub == "test-service"
    assert sample_service_access_token_payload.aud == "test-audience"
    assert sample_service_access_token_payload.scope == ["read", "write"]
    assert sample_service_access_token_payload.type == "service"
    assert isinstance(sample_service_access_token_payload.exp, datetime.datetime)


def test_service_access_token_payload_allows_empty_values() -> None:
    payload = ServiceAccessTokenPayload(
        sub="",
        aud="",
        scope=[],
        type="",
    )

    assert payload.sub == ""
    assert payload.aud == ""
    assert payload.scope == []
    assert payload.type == ""
