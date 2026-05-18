import redis.asyncio as aioredis
from database.schemas import ProductOut
from services.a_product_service import AProductService
from services.cache.a_base_cache_service import ABaseCacheService


class AProductCacheService(ABaseCacheService):
    def __init__(
        self,
        *,
        redis_client: aioredis.Redis,
        product_service: AProductService,
    ):
        super().__init__(redis_client=redis_client)
        self.product_service = product_service

    async def get_cached_product(self, *, product_id: int) -> ProductOut:
        key = self._build_key("products:one", product_id=product_id)

        async def loader():
            return await self.product_service.get_product_by_id(product_id=product_id)

        return await self._get_or_set(
            key=key,
            ttl=600,
            loader=loader,
        )

    async def get_cached_products(self) -> list[ProductOut]:
        key = self._build_key("products:all")

        async def loader():
            return await self.product_service.get_products()

        result = await self._get_or_set(
            key=key,
            ttl=600,
            loader=loader,
        )
        return result or []

    async def invalidate_product(self, *, product_id: int) -> None:
        key = self._build_key("products:one", product_id=product_id)
        await self._invalidate(key=key)

    async def invalidate_products(self) -> None:
        key = self._build_key("products:all")
        await self._invalidate(key=key)
