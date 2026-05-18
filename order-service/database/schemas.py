from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

# ─── BaseSchema ───────────────────────────────────────────────────────────────


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ─── Order ────────────────────────────────────────────────────────────────────


class OrderCreate(BaseModel):
    user_id: int | None = Field(
        None,
        gt=0,
        description="ID клиента (необязательно, > 0)",
    )
    total: Decimal = Field(
        ...,
        gt=0,
        max_digits=10,
        decimal_places=2,
        description="Общая стоимость заказа (обязательно, > 0)",
    )


class OrderOut(BaseSchema):
    id: int
    user_id: int
    total: Decimal


# ─── OrderItem ────────────────────────────────────────────────────────────────


class OrderItemCreate(BaseModel):
    order_id: int = Field(..., gt=0, description="ID заказа (обязательно, > 0)")
    product_id: int = Field(..., gt=0, description="ID товара (обязательно, > 0)")
    quantity: int = Field(..., gt=0, description="Количество (обязательно, > 0)")
    price: Decimal = Field(
        ...,
        gt=0,
        max_digits=10,
        decimal_places=2,
        description="Цена позиции (обязательно, > 0)",
    )


class OrderItemOut(BaseSchema):
    id: int
    order_id: int
    product_id: int
    quantity: int
    price: Decimal


# ─── Auth ────────────────────────────────────────────────────────────────────


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


# ─── Report ──────────────────────────────────────────────────────────────────


class ReportCreate(BaseModel):
    order_id: int = Field(..., gt=0, description="ID заказа (обязательно, > 0)")
    user_id: int = Field(..., gt=0, description="ID пользователя (обязательно, > 0)")
    total: Decimal = Field(
        ...,
        gt=0,
        max_digits=10,
        decimal_places=2,
        description="Сумма заказа (обязательно, > 0)",
    )


class ReportOut(BaseSchema):
    order_id: int
    user_id: int
    total: Decimal
