from api.dependencies.limiter import limiter
from api.dependencies.services import (
    get_user_cache_service,
    get_user_write_service,
)
from database.schemas import UserCreate, UserOut, UserWithPasswordOut
from fastapi import APIRouter, Depends, Request, status
from pydantic import EmailStr
from services.a_user_service import AUserService
from services.cache.a_user_cache_service import AUserCacheService

users_router = APIRouter(prefix="/users")


@users_router.get(
    "/by-email/{email}",
    summary="Получить пользвателя по почте (v2, Redis-кэш)",
    status_code=status.HTTP_200_OK,
    response_model=UserWithPasswordOut,
)
@limiter.limit("20/minute")
async def v2_get_user_by_email(
    request: Request,
    email: EmailStr,
    user_cache: AUserCacheService = Depends(get_user_cache_service),
):
    return await user_cache.get_cached_user_by_email(email=email)


@users_router.get(
    "/{user_id}",
    summary="Получить пользователя по ID (v2, Redis-кэш)",
    status_code=status.HTTP_200_OK,
    response_model=UserOut,
)
@limiter.limit("100/minute")
async def v2_get_user(
    request: Request,
    user_id: int,
    user_cache: AUserCacheService = Depends(get_user_cache_service),
):
    return await user_cache.get_cached_user(user_id=user_id)


@users_router.post(
    "/",
    summary="Создать пользователя (v2, с инвалидацией кэша)",
    status_code=status.HTTP_201_CREATED,
    response_model=UserOut,
)
@limiter.limit("20/minute")
async def v2_create_user(
    request: Request,
    new_user: UserCreate,
    user_service: AUserService = Depends(get_user_write_service),
    user_cache: AUserCacheService = Depends(get_user_cache_service),
):
    await user_cache.invalidate_users()
    return await user_service.create_user(new_user=new_user)
