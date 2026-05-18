from typing import List

from database.models import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class AUserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def db_create_user(
        self,
        *,
        name: str,
        email: str,
        password_hash: str,
    ) -> User:
        user = User(
            name=name,
            email=email,
            password_hash=password_hash,
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def db_get_user_by_id(self, *, user_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def db_get_user_by_email(self, *, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def db_get_users(self) -> List[User]:
        result = await self.session.execute(select(User).order_by(User.id))
        return list(result.scalars().all())

    async def db_update_user(
        self,
        *,
        user_id: int,
        name: str | None = None,
        email: str | None = None,
        password_hash: str | None = None,
    ) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            return None

        if name is not None:
            user.name = name
        if email is not None:
            user.email = email
        if password_hash is not None:
            user.password_hash = password_hash

        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def db_delete_user_by_id(self, *, user_id: int) -> bool:
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            return False

        await self.session.delete(user)
        return True
