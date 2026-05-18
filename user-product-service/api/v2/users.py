from api.app import get_user_cache_service, get_user_write_service, limiter, v2_router
from database.schemas import UserCreate, UserOut, UserUpdate
from fastapi import Depends, Request, status
from services.a_user_service import AUserService
from services.cache.a_user_cache_service import AUserCacheService


@v2_router.get(
    "/users",
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


@v2_router.get(
    "/users/{user_id}",
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


@v2_router.post(
    "/users",
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


@v2_router.put(
    "/users/{user_id}",
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


@v2_router.delete(
    "/users/{user_id}",
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
