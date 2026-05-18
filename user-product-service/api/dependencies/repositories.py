from database.connection import get_read_session, get_write_session
from fastapi import Depends
from repository.a_product_repository import AProductRepository
from repository.a_service_token_repository import AServiceTokenRepository
from repository.a_user_repository import AUserRepository

# ——— DI: internal repositories ———————————————————————————————————————————————


async def get_service_token_repository(
    session=Depends(get_write_session),
) -> AServiceTokenRepository:
    return AServiceTokenRepository(session=session)


# ——— DI: read repositories ———————————————————————————————————————————————————


async def get_user_read_repository(
    session=Depends(get_read_session),
) -> AUserRepository:
    return AUserRepository(session=session)


async def get_product_read_repository(
    session=Depends(get_read_session),
) -> AProductRepository:
    return AProductRepository(session=session)


# ——— DI: write repositories ——————————————————————————————————————————————————


async def get_user_write_repository(
    session=Depends(get_write_session),
) -> AUserRepository:
    return AUserRepository(session=session)


async def get_product_write_repository(
    session=Depends(get_write_session),
) -> AProductRepository:
    return AProductRepository(session=session)
