from api.app import (
    cache_dep,
    get_user_read_service,
    get_user_write_service,
    limiter,
    v1_router,
)
from database.schemas import UserCreate, UserOut, UserUpdate
from fastapi import Depends, Request, status
from services.a_user_service import AUserService


@v1_router.get(
    "/users",
    summary="Получить список пользователей",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(cache_dep())],
    response_model=list[UserOut],
)
@limiter.limit("100/minute")
async def v1_get_users(
    request: Request,
    user_service: AUserService = Depends(get_user_read_service),
):
    return await user_service.get_users()


@v1_router.get(
    "/users/{user_id}",
    summary="Получить пользователя по ID",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(cache_dep())],
    response_model=UserOut,
)
@limiter.limit("100/minute")
async def v1_get_user(
    request: Request,
    user_id: int,
    user_service: AUserService = Depends(get_user_read_service),
):
    return await user_service.get_user_by_id(user_id=user_id)


@v1_router.post(
    "/users",
    summary="Создать пользователя",
    status_code=status.HTTP_201_CREATED,
    response_model=UserOut,
)
@limiter.limit("20/minute")
async def v1_create_user(
    request: Request,
    new_user: UserCreate,
    user_service: AUserService = Depends(get_user_write_service),
):
    return await user_service.create_user(new_user=new_user)


@v1_router.put(
    "/users/{user_id}",
    summary="Обновить пользователя",
    status_code=status.HTTP_200_OK,
    response_model=UserOut,
)
@limiter.limit("20/minute")
async def v1_update_user(
    request: Request,
    user_id: int,
    new_user: UserUpdate,
    user_service: AUserService = Depends(get_user_write_service),
):
    return await user_service.update_user(
        user_id=user_id,
        new_user=new_user,
    )


@v1_router.delete(
    "/users/{user_id}",
    summary="Удалить пользователя",
    status_code=status.HTTP_204_NO_CONTENT,
)
@limiter.limit("10/minute")
async def v1_delete_user(
    request: Request,
    user_id: int,
    user_service: AUserService = Depends(get_user_write_service),
):
    await user_service.delete_user_by_id(user_id=user_id)
