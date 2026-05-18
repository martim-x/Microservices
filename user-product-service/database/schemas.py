import html
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# ─── BaseSchema ───────────────────────────────────────────────────────────────


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ─── Product ──────────────────────────────────────────────────────────────────


class ProductCreate(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Название товара (обязательно, 1–100 символов)",
    )
    price: Decimal = Field(
        ...,
        gt=0,
        max_digits=10,
        decimal_places=2,
        description="Цена товара (обязательно, > 0)",
    )
    quantity: int = Field(
        ...,
        gt=0,
        description="Количество на складе (обязательно, > 0)",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        sanitized = html.escape(v.strip())
        if not sanitized:
            raise ValueError("Название не может состоять только из пробелов")
        return sanitized


class ProductUpdate(BaseModel):
    name: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        description="Название товара (необязательно, 1–100 символов)",
    )
    price: Decimal | None = Field(
        None,
        gt=0,
        max_digits=10,
        decimal_places=2,
        description="Цена товара (необязательно, > 0)",
    )
    quantity: int | None = Field(
        None,
        gt=0,
        description="Количество на складе (необязательно, > 0)",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        sanitized = html.escape(v.strip())
        if not sanitized:
            raise ValueError("Название не может состоять только из пробелов")
        return sanitized


class ProductOut(BaseSchema):
    id: int
    name: str
    price: Decimal
    quantity: int


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


class UserUpdate(BaseModel):
    name: str | None = Field(
        None,
        min_length=1,
        max_length=50,
        description="Имя пользователя (необязательно, 1–50 символов)",
    )
    email: EmailStr | None = Field(
        None,
        description="Email пользователя (необязательно)",
    )
    password: str | None = Field(
        None,
        min_length=8,
        max_length=100,
        description="Новый пароль (необязательно, 8–100 символов)",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is None:  # ← исправлено: сначала проверяем None
            return None
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


# ─── Auth ─────────────────────────────────────────────────────────────────────


class AccessTokenPayload(BaseModel):
    user_id: int = Field(..., gt=0, description="ID пользователя")
    name: str = Field(..., max_length=50, description="Имя пользователя")
    email: str = Field(..., description="Email пользователя")


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
