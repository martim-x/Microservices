from datetime import UTC, datetime

from database.models import Auth
from sqlalchemy import false, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class AAuthRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def db_create_refresh_token(
        self,
        *,
        user_id: int,
        refresh_token_hash: str,
        expires_at: datetime,
    ) -> Auth:
        token = Auth(
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
        )
        self.session.add(token)
        await self.session.flush()
        await self.session.refresh(token)
        return token

    async def db_get_refresh_token(
        self,
        *,
        refresh_token_hash: str,
    ) -> Auth | None:
        result = await self.session.execute(
            select(Auth)
            .options(selectinload(Auth.user))
            .where(Auth.refresh_token_hash == refresh_token_hash)
            .where(Auth.is_revoked == false())
            .where(Auth.expires_at > datetime.now(UTC))
        )
        return result.scalar_one_or_none()

    async def db_revoke_refresh_token(
        self,
        *,
        refresh_token_hash: str,
    ) -> bool:
        result = await self.session.execute(
            select(Auth).where(Auth.refresh_token_hash == refresh_token_hash)
        )
        refresh_token = result.scalar_one_or_none()
        if refresh_token is None:
            return False

        refresh_token.is_revoked = True
        return True
