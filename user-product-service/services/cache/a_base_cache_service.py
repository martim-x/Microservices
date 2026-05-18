import json

import redis.asyncio as aioredis
from pydantic import BaseModel


class ABaseCacheService:
    def __init__(self, *, redis_client: aioredis.Redis):
        self.redis = redis_client

    @staticmethod
    def _build_key(prefix: str, *args, **kwargs) -> str:
        key_parts = [prefix]

        if args:
            key_parts.append(str(args))

        if kwargs:
            key_parts.append(str(sorted(kwargs.items())))

        return ":".join(key_parts)

    @staticmethod
    def _to_jsonable(value):
        if value is None:
            return None

        if isinstance(value, BaseModel):
            return value.model_dump(mode="json")

        if isinstance(value, list):
            return [ABaseCacheService._to_jsonable(item) for item in value]

        if isinstance(value, tuple):
            return [ABaseCacheService._to_jsonable(item) for item in value]

        if isinstance(value, dict):
            return {
                key: ABaseCacheService._to_jsonable(val) for key, val in value.items()
            }

        return value

    async def _get_or_set(
        self,
        *,
        key: str,
        ttl: int,
        loader,
    ):
        cached = await self.redis.get(key)
        if cached is not None:
            return json.loads(cached)

        result = await loader()
        if result is None:
            return None

        payload = self._to_jsonable(result)
        await self.redis.setex(key, ttl, json.dumps(payload))
        return payload

    async def _invalidate(self, *, key: str) -> None:
        await self.redis.delete(key)
