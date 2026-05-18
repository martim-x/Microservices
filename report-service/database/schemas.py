from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

# ─── BaseSchema ─────────────────────────────────────────────────────F──────────


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


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
