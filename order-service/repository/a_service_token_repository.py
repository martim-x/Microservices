import json

from database.models import ServiceToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class AServiceTokenRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def db_create_service_token(
        self,
        *,
        service_name: str,
        service_secret_hash: str,
        allowed_audience: str,
        allowed_scopes: list[str],
    ) -> ServiceToken:
        token = ServiceToken(
            service_name=service_name,
            service_secret_hash=service_secret_hash,
            allowed_audience=allowed_audience,
            allowed_scopes=json.dumps(allowed_scopes),
        )
        self.session.add(token)
        await self.session.flush()
        await self.session.refresh(token)
        return token

    async def db_get_service_token_by_name(
        self,
        *,
        service_name: str,
    ) -> ServiceToken | None:
        result = await self.session.execute(
            select(ServiceToken).where(ServiceToken.service_name == service_name)
        )
        return result.scalar_one_or_none()

    async def db_disable_service_token(
        self,
        *,
        service_name: str,
    ) -> bool:
        result = await self.session.execute(
            select(ServiceToken).where(ServiceToken.service_name == service_name)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return False

        row.is_active = False
        return True
