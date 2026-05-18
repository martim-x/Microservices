from api.dependencies.limiter import limiter
from api.dependencies.services import get_auth_service, get_service_token_service
from api.settings import settings
from database.schemas import (
    AccessTokenPayload,
    TokenPairResponse,
    UserCreate,
    UserLogin,
    UserOut,
)
from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from services.a_auth_service import AAuthService
from services.a_service_token_service import AServiceTokenService
from services.exceptions import UnauthorizedError

auth_router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
)


COOKIE_PARAMS = {
    "key": "refresh_token",
    "httponly": True,
    "secure": False,
    "samesite": "lax",
    "max_age": 30 * 24 * 60 * 60,
}


@auth_router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("20/minute")
async def register(
    request: Request,
    new_user: UserCreate,
    auth_service: AAuthService = Depends(get_auth_service),
    service_token_service: AServiceTokenService = Depends(get_service_token_service),
):
    service_access_token = await service_token_service.issue_service_access_token(
        service_name=settings.AUTH_SERVICE_NAME,
        service_secret=settings.SERVICE_SECRET_KEY,
        audience=settings.USER_PRODUCT_SERVICE_NAME,
    )

    return await auth_service.register(
        new_user=new_user,
        service_access_token=service_access_token,
    )


@auth_router.post(
    "/login",
    response_model=TokenPairResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit("20/minute")
async def login(
    request: Request,
    credentials: UserLogin,
    response: Response,
    auth_service: AAuthService = Depends(get_auth_service),
    service_token_service: AServiceTokenService = Depends(get_service_token_service),
):
    service_access_token = await service_token_service.issue_service_access_token(
        service_name=settings.AUTH_SERVICE_NAME,
        service_secret=settings.SERVICE_SECRET_KEY,
        audience=settings.USER_PRODUCT_SERVICE_NAME,
    )

    tokens = await auth_service.login(
        email=credentials.email,
        password=credentials.password,
        service_access_token=service_access_token,
    )

    response.set_cookie(
        value=tokens["refresh_token"],
        **COOKIE_PARAMS,
    )

    return TokenPairResponse(
        access_token=tokens["access_token"],
        token_type="bearer",
    )


@auth_router.post(
    "/refresh",
    response_model=TokenPairResponse,
    status_code=status.HTTP_200_OK,
    summary="Обновление access token",
)
@limiter.limit("20/minute")
async def refresh_token(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    auth_service: AAuthService = Depends(get_auth_service),
):
    if refresh_token is None:
        raise UnauthorizedError("Refresh-токен отсутствует")

    result = await auth_service.refresh(refresh_token=refresh_token)

    response.set_cookie(
        value=result["refresh_token"],
        **COOKIE_PARAMS,
    )

    return TokenPairResponse(
        access_token=result["access_token"],
        token_type="bearer",
    )


@auth_router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Выход пользователя",
)
@limiter.limit("20/minute")
async def logout(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    auth_service: AAuthService = Depends(get_auth_service),
):
    if refresh_token:
        await auth_service.logout(refresh_token=refresh_token)

    response.delete_cookie("refresh_token")


@auth_router.get(
    "/verify/{access_token}",
    response_model=AccessTokenPayload,
    status_code=status.HTTP_200_OK,
    summary="Аутентификация пользователя",
)
@limiter.limit("100/minute")
async def verify(
    request: Request,
    access_token: str,
    auth_service: AAuthService = Depends(get_auth_service),
):
    token_data = auth_service.verify_access_token(access_token)
    if token_data is None:
        raise UnauthorizedError("Неверный или истёкший токен")
    return token_data
