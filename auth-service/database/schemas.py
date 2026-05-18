import html
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# ─── BaseSchema ───────────────────────────────────────────────────────────────


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ─── Auth ─────────────────────────────────────────────────────────────────────


class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="Email пользователя (обязательно)")
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Пароль (обязательно, 8–100 символов)",
    )


class AccessTokenPayload(BaseModel):
    user_id: int = Field(..., gt=0, description="ID пользователя")
    name: str = Field(..., max_length=50, description="Имя пользователя")
    email: str = Field(..., description="Email пользователя")


class TokenPairResponse(BaseModel):
    access_token: str = Field(..., description="JWT access-токен (TTL 15 минут)")
    token_type: str = Field(default="bearer", description="Тип токена, всегда bearer")


class AuthTokenOut(BaseSchema):
    id: int
    user_id: int
    expires_at: datetime
    is_revoked: bool


# ─── User ─────────────────────────────────────────────────────────────────────


class UserCreate(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Имя пользователя (обязательно, 1–50 символов)",
    )
    email: EmailStr = Field(
        ...,
        description="Email пользователя (обязательно, уникальный)",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Пароль (обязательно, 8–100 символов)",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        sanitized = html.escape(v.strip())
        if not sanitized:
            raise ValueError("Имя не может состоять только из пробелов")
        return sanitized


class UserOut(BaseSchema):
    id: int
    name: str
    email: EmailStr
    created_at: datetime


class UserWithPasswordOut(BaseSchema):
    id: int
    name: str
    email: EmailStr
    password_hash: str
    created_at: datetime


# ─── ServiceToken ───────────────────────────────────────────────────────────────


class ServiceTokenCreate(BaseModel):
    service_name: str = Field(min_length=1, max_length=100)
    service_secret: str = Field(min_length=16)
    allowed_audience: str = Field(min_length=1, max_length=100)
    allowed_scopes: list[str]


class ServiceTokenOut(BaseModel):
    id: int
    service_name: str
    allowed_audience: str
    allowed_scopes: list[str]
    is_active: bool
    created_at: datetime


class ServiceAccessTokenPayload(BaseModel):
    sub: str
    aud: str
    scope: list[str]
    type: str
    exp: datetime | None = None
