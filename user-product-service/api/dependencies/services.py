import redis.asyncio as aioredis
from api.dependencies.repositories import (
    get_product_read_repository,
    get_product_write_repository,
    get_service_token_repository,
    get_user_read_repository,
    get_user_write_repository,
)
from fastapi import Depends, Request
from repository.a_product_repository import AProductRepository
from repository.a_service_token_repository import AServiceTokenRepository
from repository.a_user_repository import AUserRepository
from services.a_exchange_service import AExchangeService
from services.a_product_service import AProductService
from services.a_service_token_service import AServiceTokenService
from services.a_user_service import AUserService
from services.cache.a_product_cache_service import AProductCacheService
from services.cache.a_user_cache_service import AUserCacheService

# ——— DI: internal services ———————————————————————————————————————————————————


async def get_service_token_service(
    service_token_repository: AServiceTokenRepository = Depends(
        get_service_token_repository
    ),
) -> AServiceTokenService:
    return AServiceTokenService(service_token_repository=service_token_repository)


# ——— DI: read services ———————————————————————————————————————————————————————


async def get_user_read_service(
    user_repo: AUserRepository = Depends(get_user_read_repository),
) -> AUserService:
    return AUserService(user_repository=user_repo)


async def get_product_read_service(
    product_repo: AProductRepository = Depends(get_product_read_repository),
) -> AProductService:
    return AProductService(product_repository=product_repo)


# ——— DI: write services ——————————————————————————————————————————————————————


async def get_user_write_service(
    user_repo: AUserRepository = Depends(get_user_write_repository),
) -> AUserService:
    return AUserService(user_repository=user_repo)


async def get_product_write_service(
    product_repo: AProductRepository = Depends(get_product_write_repository),
) -> AProductService:
    return AProductService(product_repository=product_repo)


# ——— DI: redis ———————————————————————————————————————————————————————————————


async def get_redis_client(request: Request):
    return request.app.state.redis_client


# ——— DI: cache services (v2) — read-only, slave ———————————————————————————————


async def get_user_cache_service(
    redis_client: aioredis.Redis = Depends(get_redis_client),
    user_service: AUserService = Depends(get_user_read_service),
) -> AUserCacheService:
    return AUserCacheService(
        redis_client=redis_client,
        user_service=user_service,
    )


async def get_product_cache_service(
    redis_client: aioredis.Redis = Depends(get_redis_client),
    product_service: AProductService = Depends(get_product_read_service),
) -> AProductCacheService:
    return AProductCacheService(
        redis_client=redis_client,
        product_service=product_service,
    )


# ——— DI: exchange service ————————————————————————————————————————————————————


async def get_exchange_service() -> AExchangeService:
    return AExchangeService()
