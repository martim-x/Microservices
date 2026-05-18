from api.dependencies.repositories import (
    get_auth_repository,
    get_service_token_repository,
)
from fastapi import Depends
from repository.a_auth_repository import AAuthRepository
from repository.a_service_token_repository import AServiceTokenRepository
from services.a_auth_service import AAuthService
from services.a_service_token_service import AServiceTokenService


async def get_auth_service(
    auth_repo: AAuthRepository = Depends(get_auth_repository),
) -> AAuthService:
    return AAuthService(
        auth_repository=auth_repo,
    )


async def get_service_token_service(
    service_token_repository: AServiceTokenRepository = Depends(
        get_service_token_repository
    ),
) -> AServiceTokenService:
    return AServiceTokenService(service_token_repository=service_token_repository)
