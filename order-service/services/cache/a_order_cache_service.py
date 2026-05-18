from database.schemas import OrderOut
from services.a_order_service import AOrderService
from services.cache.a_base_cache_service import ABaseCacheService


class AOrderCacheService(ABaseCacheService):
    def __init__(
        self,
        *,
        redis_client,
        order_service: AOrderService,
    ):
        super().__init__(redis_client=redis_client)
        self.order_service = order_service

    async def get_cached_order(self, *, order_id: int) -> OrderOut:
        key = self._build_key("orders:one", order_id=order_id)

        async def loader():
            return await self.order_service.get_order_by_id(order_id=order_id)

        return await self._get_or_set(
            key=key,
            ttl=600,
            loader=loader,
        )

    async def get_cached_orders(self) -> list[OrderOut]:
        key = self._build_key("orders:all")

        async def loader():
            return await self.order_service.get_orders()

        result = await self._get_or_set(
            key=key,
            ttl=600,
            loader=loader,
        )
        return result or []

    async def invalidate_order(self, *, order_id: int) -> None:
        key = self._build_key("orders:one", order_id=order_id)
        await self._invalidate(key=key)

    async def invalidate_orders(self) -> None:
        key = self._build_key("orders:all")
        await self._invalidate(key=key)
