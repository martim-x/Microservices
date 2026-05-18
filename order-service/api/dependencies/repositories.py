from database.connection import get_read_session, get_write_session
from fastapi import Depends
from repository.a_order_item_repository import AOrderItemRepository
from repository.a_order_repository import AOrderRepository
from repository.a_service_token_repository import AServiceTokenRepository

# ——— DI: internal repositories ———————————————————————————————————————————————


async def get_service_token_repository(
    session=Depends(get_write_session),
) -> AServiceTokenRepository:
    return AServiceTokenRepository(session=session)


# ——— DI: read repositories ———————————————————————————————————————————————————


async def get_order_read_repository(
    session=Depends(get_read_session),
) -> AOrderRepository:
    return AOrderRepository(session=session)


async def get_order_item_read_repository(
    session=Depends(get_read_session),
) -> AOrderItemRepository:
    return AOrderItemRepository(session=session)


# ——— DI: write repositories ——————————————————————————————————————————————————


async def get_order_write_repository(
    session=Depends(get_write_session),
) -> AOrderRepository:
    return AOrderRepository(session=session)


async def get_order_item_write_repository(
    session=Depends(get_write_session),
) -> AOrderItemRepository:
    return AOrderItemRepository(session=session)
