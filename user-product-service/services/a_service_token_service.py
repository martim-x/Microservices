import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from api.settings import settings
from database.schemas import (
    ServiceAccessTokenPayload,
    ServiceTokenCreate,
    ServiceTokenOut,
)
from jwt.exceptions import InvalidTokenError
from repository.a_service_token_repository import AServiceTokenRepository
from services.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationServiceError,
)

SERVICE_SECRET_KEY = settings.SERVICE_SECRET_KEY
ALGORITHM = settings.ALGORITHM
SERVICE_ACCESS_TOKEN_TTL = timedelta(minutes=settings.SERVICE_ACCESS_TOKEN_TTL)


class AServiceTokenService:
    def __init__(self, service_token_repository: AServiceTokenRepository):
        self.service_token_repository = service_token_repository

    @staticmethod
    def hash_service_secret(service_secret: str) -> str:
        return hashlib.sha256(service_secret.encode()).hexdigest()

    @staticmethod
    def generate_service_secret() -> str:
        return secrets.token_urlsafe(64)

    @staticmethod
    def _deserialize_scopes(raw_scopes: str) -> list[str]:
        try:
            scopes = json.loads(raw_scopes)
        except json.JSONDecodeError as e:
            raise ValidationServiceError(
                "allowed_scopes содержит невалидный JSON"
            ) from e

        if not isinstance(scopes, list) or not all(isinstance(x, str) for x in scopes):
            raise ValidationServiceError("allowed_scopes должен быть list[str]")

        return scopes

    async def register_service(
        self, *, new_service: ServiceTokenCreate
    ) -> ServiceTokenOut:
        existing = await self.service_token_repository.db_get_service_token_by_name(
            service_name=new_service.service_name
        )
        if existing:
            raise ConflictError("Сервис с таким именем уже существует")

        token = await self.service_token_repository.db_create_service_token(
            service_name=new_service.service_name,
            service_secret_hash=self.hash_service_secret(new_service.service_secret),
            allowed_audience=new_service.allowed_audience,
            allowed_scopes=new_service.allowed_scopes,
        )
        await self.service_token_repository.session.commit()

        return ServiceTokenOut(
            id=token.id,
            service_name=token.service_name,
            allowed_audience=token.allowed_audience,
            allowed_scopes=self._deserialize_scopes(token.allowed_scopes),
            is_active=token.is_active,
            created_at=token.created_at,
        )

    async def issue_service_access_token(
        self,
        *,
        service_name: str,
        service_secret: str,
        audience: str,
    ) -> str:
        token = await self.service_token_repository.db_get_service_token_by_name(
            service_name=service_name
        )
        if not token or not token.is_active:
            raise NotFoundError("Сервис недоступен")

        if not hmac.compare_digest(
            self.hash_service_secret(service_secret),
            token.service_secret_hash,
        ):
            raise UnauthorizedError("Неверные service credentials")

        if token.allowed_audience != audience:
            raise ForbiddenError("Недопустимый audience")

        payload = {
            "sub": token.service_name,
            "aud": audience,
            "scope": self._deserialize_scopes(token.allowed_scopes),
            "type": "service_access",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + SERVICE_ACCESS_TOKEN_TTL,
        }

        return jwt.encode(payload=payload, key=SERVICE_SECRET_KEY, algorithm=ALGORITHM)

    @staticmethod
    def verify_service_access_token(
        *,
        service_access_token: str,
        expected_audience: str,
    ) -> ServiceAccessTokenPayload:
        if not service_access_token:
            raise UnauthorizedError("Пустой service access token")

        try:
            data = jwt.decode(
                jwt=service_access_token,
                key=SERVICE_SECRET_KEY,
                algorithms=[ALGORITHM],
                audience=expected_audience,
            )
        except InvalidTokenError as e:
            raise UnauthorizedError("Невалидный service access token") from e

        if data.get("type") != "service_access":
            raise UnauthorizedError("Неверный type токена")

        sub = data.get("sub")
        aud = data.get("aud")
        scope = data.get("scope", [])

        if not isinstance(sub, str) or not sub:
            raise UnauthorizedError("Отсутствует sub")
        if not isinstance(aud, str) or not aud:
            raise UnauthorizedError("Отсутствует aud")
        if not isinstance(scope, list) or not all(isinstance(x, str) for x in scope):
            raise UnauthorizedError("Некорректный scope")

        return ServiceAccessTokenPayload(
            sub=sub,
            aud=aud,
            scope=scope,
            type="service_access",
        )

    @staticmethod
    def require_scope(
        *,
        service_access_token_payload: ServiceAccessTokenPayload,
        required_scope: str,
    ) -> None:
        if required_scope not in service_access_token_payload.scope:
            raise ForbiddenError("Недостаточно прав у сервиса")
