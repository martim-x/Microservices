import bcrypt
from database.schemas import UserCreate, UserOut, UserUpdate, UserWithPasswordOut
from repository.a_user_repository import AUserRepository
from services.exceptions import ConflictError, NotFoundError


class AUserService:
    def __init__(self, user_repository: AUserRepository):
        self.user_repository = user_repository

    async def create_user(self, *, new_user: UserCreate) -> UserOut:
        try:
            existing_user = await self.user_repository.db_get_user_by_email(
                email=new_user.email
            )
            if existing_user is not None:
                raise ConflictError("Пользователь с такой почтой уже существует")

            password_hash = bcrypt.hashpw(
                new_user.password.encode(),
                bcrypt.gensalt(),
            ).decode()

            user = await self.user_repository.db_create_user(
                name=new_user.name,
                email=new_user.email,
                password_hash=password_hash,
            )

            await self.user_repository.session.commit()
            return UserOut.model_validate(user)
        except Exception:
            await self.user_repository.session.rollback()
            raise

    async def get_user_by_id(self, *, user_id: int) -> UserOut:
        try:
            user = await self.user_repository.db_get_user_by_id(user_id=user_id)
            if user is None:
                raise NotFoundError("Пользователь не найден")

            await self.user_repository.session.commit()
            return UserOut.model_validate(user)
        except Exception:
            await self.user_repository.session.rollback()
            raise

    async def get_user_by_email(self, *, email: str) -> UserWithPasswordOut:
        try:
            user = await self.user_repository.db_get_user_by_email(email=email)
            if user is None:
                raise NotFoundError("Пользователь не найден")

            await self.user_repository.session.commit()
            return UserWithPasswordOut.model_validate(user)
        except Exception:
            await self.user_repository.session.rollback()
            raise

    async def get_users(self) -> list[UserOut]:
        try:
            users = await self.user_repository.db_get_users()
            await self.user_repository.session.commit()
            return [UserOut.model_validate(user) for user in users]
        except Exception:
            await self.user_repository.session.rollback()
            raise

    async def update_user(self, *, user_id: int, new_user: UserUpdate) -> UserOut:
        try:
            update_kwargs: dict = {}

            if new_user.name is not None:
                update_kwargs["name"] = new_user.name
            if new_user.email is not None:
                update_kwargs["email"] = new_user.email
            if new_user.password is not None:
                update_kwargs["password_hash"] = bcrypt.hashpw(
                    new_user.password.encode(),
                    bcrypt.gensalt(),
                ).decode()

            user = await self.user_repository.db_update_user(
                user_id=user_id,
                **update_kwargs,
            )
            if user is None:
                raise NotFoundError("Пользователь не найден")

            await self.user_repository.session.commit()
            return UserOut.model_validate(user)
        except Exception:
            await self.user_repository.session.rollback()
            raise

    async def delete_user_by_id(self, *, user_id: int) -> bool:
        try:
            deleted = await self.user_repository.db_delete_user_by_id(user_id=user_id)
            if not deleted:
                raise NotFoundError("Пользователь не найден")

            await self.user_repository.session.commit()
            return True
        except Exception:
            await self.user_repository.session.rollback()
            raise
