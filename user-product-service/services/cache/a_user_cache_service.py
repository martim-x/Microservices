from database.schemas import UserOut, UserWithPasswordOut
from services.a_user_service import AUserService
from services.cache.a_base_cache_service import ABaseCacheService


class AUserCacheService(ABaseCacheService):
    def __init__(
        self,
        *,
        redis_client,
        user_service: AUserService,
    ):
        super().__init__(redis_client=redis_client)
        self.user_service = user_service

    async def get_cached_user_by_email(self, *, email: str) -> UserWithPasswordOut:
        key = self._build_key("users:one", email=email)

        async def loader():
            return await self.user_service.get_user_by_email(email=email)

        return await self._get_or_set(
            key=key,
            ttl=600,
            loader=loader,
        )

    async def get_cached_user(self, *, user_id: int) -> UserOut:
        key = self._build_key("users:one", user_id=user_id)

        async def loader():
            return await self.user_service.get_user_by_id(user_id=user_id)

        return await self._get_or_set(
            key=key,
            ttl=600,
            loader=loader,
        )

    async def get_cached_users(self) -> list[UserOut]:
        key = self._build_key("users:all")

        async def loader():
            return await self.user_service.get_users()

        result = await self._get_or_set(
            key=key,
            ttl=600,
            loader=loader,
        )
        return result or []

    async def invalidate_user(self, *, user_id: int) -> None:
        key = self._build_key("users:one", user_id=user_id)
        await self._invalidate(key=key)

    async def invalidate_user_by_email(self, *, email: str) -> None:
        key = self._build_key("users:one", email=email)
        await self._invalidate(key=key)

    async def invalidate_users(self) -> None:
        key = self._build_key("users:all")
        await self._invalidate(key=key)
