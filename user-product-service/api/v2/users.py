from api.dependencies.limiter import limiter
from api.dependencies.services import (
    get_user_cache_service,
    get_user_write_service,
)
from database.schemas import UserCreate, UserOut, UserUpdate
from fastapi import APIRouter, Depends, Request, status
from services.a_user_service import AUserService
from services.cache.a_user_cache_service import AUserCacheService

users_router = APIRouter(prefix="/users")


@users_router.get(
    "/",
    summary="Получить список пользователей (v2, Redis-кэш)",
    status_code=status.HTTP_200_OK,
    response_model=list[UserOut],
)
@limiter.limit("100/minute")
async def v2_get_users(
    request: Request,
    user_cache: AUserCacheService = Depends(get_user_cache_service),
):
    return await user_cache.get_cached_users()


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
async def create_user(
    request: Request,
    new_user: UserCreate,
    user_service: AUserService = Depends(get_user_write_service),
    user_cache: AUserCacheService = Depends(get_user_cache_service),
):
    user = await user_service.create_user(new_user=new_user)
    await user_cache.invalidate_users()
    return user


@users_router.put(
    "/{user_id}",
    summary="Обновить пользователя (v2, с инвалидацией кэша)",
    status_code=status.HTTP_200_OK,
    response_model=UserOut,
)
@limiter.limit("20/minute")
async def v2_update_user(
    request: Request,
    user_id: int,
    new_user: UserUpdate,
    user_service: AUserService = Depends(get_user_write_service),
    user_cache: AUserCacheService = Depends(get_user_cache_service),
):
    await user_cache.invalidate_user(user_id=user_id)
    await user_cache.invalidate_users()

    return await user_service.update_user(
        user_id=user_id,
        new_user=new_user,
    )


@users_router.delete(
    "/{user_id}",
    summary="Удалить пользователя (v2, с инвалидацией кэша)",
    status_code=status.HTTP_204_NO_CONTENT,
)
@limiter.limit("10/minute")
async def v2_delete_user(
    request: Request,
    user_id: int,
    user_service: AUserService = Depends(get_user_write_service),
    user_cache: AUserCacheService = Depends(get_user_cache_service),
):
    await user_service.delete_user_by_id(user_id=user_id)

    await user_cache.invalidate_user(user_id=user_id)
    await user_cache.invalidate_users()
