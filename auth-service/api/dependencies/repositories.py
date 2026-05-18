from database.connection import get_write_session
from fastapi import Depends
from repository.a_auth_repository import AAuthRepository
from repository.a_service_token_repository import AServiceTokenRepository


async def get_auth_repository(
    session=Depends(get_write_session),
) -> AAuthRepository:
    return AAuthRepository(session=session)


async def get_service_token_repository(
    session=Depends(get_write_session),
) -> AServiceTokenRepository:
    return AServiceTokenRepository(session=session)
