import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
import httpx
import jwt
from api.settings import settings
from database.schemas import (
    AccessTokenPayload,
    UserCreate,
    UserOut,
    UserWithPasswordOut,
)
from jwt.exceptions import DecodeError, ExpiredSignatureError, InvalidTokenError
from repository.a_auth_repository import AAuthRepository
from services.exceptions import (
    BadRequestError,
    ConflictError,
    ExternalServiceError,
    ExternalServiceUnavailableError,
    NotFoundError,
    UnauthorizedError,
    ValidationServiceError,
)

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_TTL = timedelta(minutes=settings.ACCESS_TOKEN_TTL)
REFRESH_TOKEN_TTL = timedelta(days=settings.REFRESH_TOKEN_TTL)


class AAuthService:
    def __init__(self, auth_repository: AAuthRepository):
        self.auth_repository = auth_repository

    # ----- helpers -----

    @staticmethod
    def hash_refresh_token(refresh_token: str) -> str:
        return hashlib.sha256(refresh_token.encode()).hexdigest()

    @staticmethod
    def create_refresh_token() -> tuple[str, str]:
        refresh_token = secrets.token_urlsafe(64)
        refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        return refresh_token, refresh_token_hash

    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def create_access_token(payload: AccessTokenPayload) -> str:
        data = {
            "user_id": payload.user_id,
            "name": payload.name,
            "email": payload.email,
            "type": "access",
            "exp": datetime.now(UTC) + ACCESS_TOKEN_TTL,
        }
        return jwt.encode(payload=data, key=SECRET_KEY, algorithm=ALGORITHM)

    @staticmethod
    def verify_access_token(access_token: str) -> AccessTokenPayload | None:
        try:
            data = jwt.decode(access_token, key=SECRET_KEY, algorithms=[ALGORITHM])
        except ExpiredSignatureError:
            return None
        except (DecodeError, InvalidTokenError):
            return None

        if data.get("type") != "access":
            return None

        user_id = data.get("user_id")
        name = data.get("name")
        email = data.get("email")

        if user_id is None or email is None:
            return None

        return AccessTokenPayload(
            user_id=int(user_id),
            name=name or "",
            email=email,
        )

    @staticmethod
    def _extract_error_detail(response: httpx.Response) -> str:
        try:
            data = response.json()
            if isinstance(data, dict):
                detail = data.get("detail")
                if isinstance(detail, str):
                    return detail
                return str(detail or data)
            return str(data)
        except Exception:
            return response.text or "Неизвестная ошибка"

    @classmethod
    def _raise_mapped_upstream_error(cls, response: httpx.Response) -> None:
        detail = cls._extract_error_detail(response)

        if response.status_code == 400:
            raise BadRequestError(detail)
        if response.status_code == 401:
            raise UnauthorizedError(detail)
        if response.status_code == 404:
            raise NotFoundError(detail)
        if response.status_code == 409:
            raise ConflictError(detail)
        if response.status_code == 422:
            raise ValidationServiceError(detail)
        if response.status_code == 503:
            raise ExternalServiceUnavailableError(detail)

        raise ExternalServiceError(
            f"user-product-service вернул {response.status_code}: {detail}"
        )

    async def _get_user_by_email_from_user_service(
        self,
        *,
        email: str,
        service_access_token: str,
    ) -> UserWithPasswordOut:
        try:
            async with httpx.AsyncClient(
                base_url=settings.USER_PRODUCT_SERVICE_URL,
                timeout=10.0,
            ) as client:
                response = await client.get(
                    url=f"/internal/users/by-email/{email}",
                    headers={
                        "Authorization": f"Bearer {service_access_token}",
                    },
                )
        except httpx.TimeoutException as e:
            raise ExternalServiceUnavailableError(
                "user-product-service не ответил вовремя"
            ) from e
        except httpx.RequestError as e:
            raise ExternalServiceUnavailableError(
                "Не удалось подключиться к user-product-service"
            ) from e

        if response.status_code >= 400:
            self._raise_mapped_upstream_error(response)

        return UserWithPasswordOut.model_validate(response.json())

    async def _create_user_in_user_service(
        self,
        *,
        new_user: UserCreate,
        service_access_token: str,
    ) -> UserOut:
        try:
            async with httpx.AsyncClient(
                base_url=settings.USER_PRODUCT_SERVICE_URL,
                timeout=10.0,
            ) as client:
                response = await client.post(
                    url="/internal/users",
                    json=new_user.model_dump(),
                    headers={
                        "Authorization": f"Bearer {service_access_token}",
                    },
                )
        except httpx.TimeoutException as e:
            raise ExternalServiceUnavailableError(
                "user-product-service не ответил вовремя"
            ) from e
        except httpx.RequestError as e:
            raise ExternalServiceUnavailableError(
                "Не удалось подключиться к user-product-service"
            ) from e

        if response.status_code >= 400:
            self._raise_mapped_upstream_error(response)

        return UserOut.model_validate(response.json())

    # ----- use-cases -----

    async def register(
        self,
        *,
        new_user: UserCreate,
        service_access_token: str,
    ) -> UserOut:
        return await self._create_user_in_user_service(
            new_user=new_user,
            service_access_token=service_access_token,
        )

    async def login(
        self,
        *,
        email: str,
        password: str,
        service_access_token: str,
    ) -> dict:
        try:
            user = await self._get_user_by_email_from_user_service(
                email=email,
                service_access_token=service_access_token,
            )

            if not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
                raise UnauthorizedError("Неверный пароль")

            access_token = self.create_access_token(
                AccessTokenPayload(
                    user_id=user.id,
                    name=user.name,
                    email=email,
                )
            )
            refresh_token, refresh_token_hash = self.create_refresh_token()
            expires_at = datetime.now(UTC) + REFRESH_TOKEN_TTL

            await self.auth_repository.db_create_refresh_token(
                user_id=user.id,
                refresh_token_hash=refresh_token_hash,
                expires_at=expires_at,
            )
            await self.auth_repository.session.commit()

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
            }
        except Exception:
            await self.auth_repository.session.rollback()
            raise

    async def refresh(self, *, refresh_token: str) -> dict:
        try:
            refresh_token_hash = self.hash_refresh_token(refresh_token)

            token_record = await self.auth_repository.db_get_refresh_token(
                refresh_token_hash=refresh_token_hash
            )
            if token_record is None or token_record.is_revoked:
                raise UnauthorizedError("Refresh-токен недействителен")
            if token_record.expires_at < datetime.now(UTC):
                raise UnauthorizedError("Refresh-токен истёк")

            await self.auth_repository.db_revoke_refresh_token(
                refresh_token_hash=refresh_token_hash
            )

            access_token = self.create_access_token(
                AccessTokenPayload(
                    user_id=token_record.user_id,
                    name=token_record.user.name,
                    email=token_record.user.email,
                )
            )
            new_refresh_token, new_refresh_token_hash = self.create_refresh_token()
            expires_at = datetime.now(UTC) + REFRESH_TOKEN_TTL

            await self.auth_repository.db_create_refresh_token(
                user_id=token_record.user_id,
                refresh_token_hash=new_refresh_token_hash,
                expires_at=expires_at,
            )
            await self.auth_repository.session.commit()

            return {
                "access_token": access_token,
                "refresh_token": new_refresh_token,
            }
        except Exception:
            await self.auth_repository.session.rollback()
            raise

    async def logout(self, *, refresh_token: str) -> bool:
        try:
            refresh_token_hash = self.hash_refresh_token(refresh_token)
            deleted = await self.auth_repository.db_revoke_refresh_token(
                refresh_token_hash=refresh_token_hash
            )
            await self.auth_repository.session.commit()
            return deleted
        except Exception:
            await self.auth_repository.session.rollback()
            raise
