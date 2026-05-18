import httpx
from api.settings import settings
from database.schemas import OrderItemCreate, OrderItemOut
from repository.a_order_item_repository import AOrderItemRepository
from repository.a_order_repository import AOrderRepository
from services.exceptions import (
    ExternalServiceError,
    NotFoundError,
    UnauthorizedError,
    ValidationServiceError,
)


class AOrderItemService:
    def __init__(
        self,
        order_item_repository: AOrderItemRepository,
        order_repository: AOrderRepository,
    ):
        self.order_item_repository = order_item_repository
        self.order_repository = order_repository

    async def create_order_item(
        self,
        *,
        new_order_item: OrderItemCreate,
        service_access_token: str,
    ) -> OrderItemOut:
        try:
            order = await self.order_repository.db_get_order_by_id(
                order_id=new_order_item.order_id
            )
            if order is None:
                raise NotFoundError("Заказ не найден")

            if new_order_item.quantity <= 0:
                raise ValidationServiceError("Количество должно быть больше нуля")

            try:
                async with httpx.AsyncClient(
                    base_url=settings.USER_PRODUCT_SERVICE_URL,
                    timeout=5.0,
                ) as client:
                    response = await client.get(
                        f"/internal/products/{new_order_item.product_id}",
                        headers={
                            "Authorization": f"Bearer {service_access_token}",
                        },
                    )
            except httpx.RequestError as e:
                raise ExternalServiceError(
                    "Не удалось обратиться к user-product-service"
                ) from e

            if response.status_code == 404:
                raise NotFoundError("Товар не найден")

            if response.status_code == 401:
                raise UnauthorizedError("Ошибка авторизации при проверке товара")

            if response.status_code >= 400:
                raise ExternalServiceError(
                    f"Ошибка user-product-service при проверке товара: "
                    f"{response.status_code}"
                )

            order_item = await self.order_item_repository.db_create_order_item(
                order_id=new_order_item.order_id,
                product_id=new_order_item.product_id,
                quantity=new_order_item.quantity,
                price=new_order_item.price,
            )

            await self.order_item_repository.session.commit()
            return OrderItemOut.model_validate(order_item)

        except Exception:
            await self.order_item_repository.session.rollback()
            raise

    async def get_order_item_by_id(self, *, order_item_id: int) -> OrderItemOut:
        try:
            order_item = await self.order_item_repository.db_get_order_item_by_id(
                order_item_id=order_item_id
            )
            if order_item is None:
                raise NotFoundError("Позиция заказа не найдена")

            await self.order_item_repository.session.commit()
            return OrderItemOut.model_validate(order_item)

        except Exception:
            await self.order_item_repository.session.rollback()
            raise

    async def get_order_items(self) -> list[OrderItemOut]:
        try:
            order_items = await self.order_item_repository.db_get_order_items()
            await self.order_item_repository.session.commit()

            return [OrderItemOut.model_validate(item) for item in order_items]

        except Exception:
            await self.order_item_repository.session.rollback()
            raise

    async def delete_order_item_by_id(self, *, order_item_id: int) -> bool:
        try:
            deleted = await self.order_item_repository.db_delete_order_item_by_id(
                order_item_id=order_item_id
            )
            if not deleted:
                raise NotFoundError("Позиция заказа не найдена")

            await self.order_item_repository.session.commit()
            return True

        except Exception:
            await self.order_item_repository.session.rollback()
            raise
