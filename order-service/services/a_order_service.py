import httpx
from api.settings import settings
from database.schemas import OrderCreate, OrderOut
from repository.a_order_repository import AOrderRepository
from services.exceptions import (
    ExternalServiceError,
    NotFoundError,
    UnauthorizedError,
    ValidationServiceError,
)


class AOrderService:
    def __init__(
        self,
        *,
        order_repository: AOrderRepository,
    ):
        self.order_repository = order_repository

    async def create_order(
        self,
        *,
        new_order: OrderCreate,
        service_access_token: str,
    ) -> OrderOut:
        try:
            if new_order.user_id is None:
                raise ValidationServiceError("Для заказа требуется user_id")

            try:
                async with httpx.AsyncClient(
                    base_url=settings.USER_PRODUCT_SERVICE_URL,
                    timeout=5.0,
                ) as client:
                    response = await client.get(
                        f"/internal/users/{new_order.user_id}",
                        headers={
                            "Authorization": f"Bearer {service_access_token}",
                        },
                    )
            except httpx.RequestError as e:
                raise ExternalServiceError(
                    "Не удалось обратиться к user-product-service"
                ) from e

            if response.status_code == 404:
                raise NotFoundError("Пользователь не найден")

            if response.status_code == 401:
                raise UnauthorizedError("Ошибка авторизации при проверке пользователя")

            if response.status_code >= 400:
                raise ExternalServiceError(
                    f"Ошибка user-product-service при проверке пользователя: "
                    f"{response.status_code}"
                )

            order = await self.order_repository.db_create_order(
                user_id=new_order.user_id,
                total=new_order.total,
            )

            await self.order_repository.session.commit()
            return OrderOut.model_validate(order)

        except Exception:
            await self.order_repository.session.rollback()
            raise

    async def get_order_by_id(self, *, order_id: int) -> OrderOut:
        try:
            order = await self.order_repository.db_get_order_by_id(order_id=order_id)
            if order is None:
                raise NotFoundError("Заказ не найден")

            await self.order_repository.session.commit()
            return OrderOut.model_validate(order)

        except Exception:
            await self.order_repository.session.rollback()
            raise

    async def get_orders(self) -> list[OrderOut]:
        try:
            orders = await self.order_repository.db_get_orders()
            await self.order_repository.session.commit()
            return [OrderOut.model_validate(order) for order in orders]

        except Exception:
            await self.order_repository.session.rollback()
            raise

    async def delete_order_by_id(self, *, order_id: int) -> bool:
        try:
            deleted = await self.order_repository.db_delete_order_by_id(
                order_id=order_id
            )
            if not deleted:
                raise NotFoundError("Заказ не найден")

            await self.order_repository.session.commit()
            return True

        except Exception:
            await self.order_repository.session.rollback()
            raise
