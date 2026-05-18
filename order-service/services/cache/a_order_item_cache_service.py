from database.schemas import OrderItemOut
from services.a_order_item_service import AOrderItemService
from services.cache.a_base_cache_service import ABaseCacheService


class AOrderItemCacheService(ABaseCacheService):
    def __init__(
        self,
        *,
        redis_client,
        order_item_service: AOrderItemService,
    ):
        super().__init__(redis_client=redis_client)
        self.order_item_service = order_item_service

    async def get_cached_order_item(self, *, order_item_id: int) -> OrderItemOut:
        key = self._build_key("order-items:one", order_item_id=order_item_id)

        async def loader():
            return await self.order_item_service.get_order_item_by_id(
                order_item_id=order_item_id
            )

        return await self._get_or_set(
            key=key,
            ttl=600,
            loader=loader,
        )

    async def get_cached_order_items(self) -> list[OrderItemOut]:
        key = self._build_key("order-items:all")

        async def loader():
            return await self.order_item_service.get_order_items()

        result = await self._get_or_set(
            key=key,
            ttl=600,
            loader=loader,
        )
        return result or []

    async def invalidate_order_item(self, *, order_item_id: int) -> None:
        key = self._build_key("order-items:one", order_item_id=order_item_id)
        await self._invalidate(key=key)

    async def invalidate_order_items(self) -> None:
        key = self._build_key("order-items:all")
        await self._invalidate(key=key)
