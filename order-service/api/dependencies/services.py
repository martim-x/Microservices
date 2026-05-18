import redis.asyncio as aioredis
from api.dependencies.repositories import (
    get_order_item_read_repository,
    get_order_item_write_repository,
    get_order_read_repository,
    get_order_write_repository,
    get_service_token_repository,
)
from fastapi import Depends, Request
from repository.a_order_item_repository import AOrderItemRepository
from repository.a_order_repository import AOrderRepository
from repository.a_service_token_repository import AServiceTokenRepository
from services.a_message_queue_service import AMessageQueueService
from services.a_order_item_service import AOrderItemService
from services.a_order_service import AOrderService
from services.a_service_token_service import AServiceTokenService
from services.cache.a_order_cache_service import AOrderCacheService
from services.cache.a_order_item_cache_service import AOrderItemCacheService

# ——— DI: internal services ———————————————————————————————————————————————————


async def get_service_token_service(
    service_token_repository: AServiceTokenRepository = Depends(
        get_service_token_repository
    ),
) -> AServiceTokenService:
    return AServiceTokenService(service_token_repository=service_token_repository)


# ——— DI: read services ———————————————————————————————————————————————————————


async def get_order_read_service(
    order_repo: AOrderRepository = Depends(get_order_read_repository),
) -> AOrderService:
    return AOrderService(
        order_repository=order_repo,
    )


async def get_order_item_read_service(
    order_item_repo: AOrderItemRepository = Depends(get_order_item_read_repository),
    order_repo: AOrderRepository = Depends(get_order_read_repository),
) -> AOrderItemService:
    return AOrderItemService(
        order_item_repository=order_item_repo,
        order_repository=order_repo,
    )


# ——— DI: write services ——————————————————————————————————————————————————————


async def get_order_write_service(
    order_repo: AOrderRepository = Depends(get_order_write_repository),
) -> AOrderService:
    return AOrderService(
        order_repository=order_repo,
    )


async def get_order_item_write_service(
    order_item_repo: AOrderItemRepository = Depends(get_order_item_write_repository),
    order_repo: AOrderRepository = Depends(get_order_write_repository),
) -> AOrderItemService:
    return AOrderItemService(
        order_item_repository=order_item_repo,
        order_repository=order_repo,
    )


# ——— DI: redis ———————————————————————————————————————————————————————————————


async def get_redis_client(request: Request):
    return request.app.state.redis_client


# ——— DI: cache services (v2) — read-only, slave ———————————————————————————————


async def get_order_cache_service(
    redis_client: aioredis.Redis = Depends(get_redis_client),
    order_service: AOrderService = Depends(get_order_read_service),
) -> AOrderCacheService:
    return AOrderCacheService(
        redis_client=redis_client,
        order_service=order_service,
    )


async def get_order_item_cache_service(
    redis_client: aioredis.Redis = Depends(get_redis_client),
    order_item_service: AOrderItemService = Depends(get_order_item_read_service),
) -> AOrderItemCacheService:
    return AOrderItemCacheService(
        redis_client=redis_client,
        order_item_service=order_item_service,
    )


# ——— DI: rabbitmq ————————————————————————————————————————————————————————————


def get_message_queue_service(request: Request) -> AMessageQueueService:
    return request.app.state.message_queue_service
