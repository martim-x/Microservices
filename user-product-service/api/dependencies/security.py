import httpx
from api.dependencies.services import get_service_token_service
from api.settings import settings
from database.schemas import AccessTokenPayload, ServiceAccessTokenPayload
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from services.a_service_token_service import AServiceTokenService

security = HTTPBearer()


async def get_current_service(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    service_token_service: AServiceTokenService = Depends(get_service_token_service),
) -> ServiceAccessTokenPayload:
    token_data = service_token_service.verify_service_access_token(
        service_access_token=credentials.credentials,
        expected_audience=settings.USER_PRODUCT_SERVICE_NAME,
    )
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный service token",
        )
    return token_data


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> AccessTokenPayload:
    async with httpx.AsyncClient(base_url=settings.AUTH_SERVICE_URL) as client:
        response = await client.get(f"/auth/verify/{credentials.credentials}")

    if response.status_code == 401:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный или истёкший токен",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ошибка проверки токена",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AccessTokenPayload.model_validate(response.json())
