from decimal import Decimal
from typing import List

from database.models import Order
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class AOrderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def db_create_order(
        self,
        *,
        user_id: int,
        total: Decimal,
    ) -> Order:
        order = Order(
            user_id=user_id,
            total=total,
        )
        self.session.add(order)
        await self.session.flush()
        await self.session.refresh(order)
        return order

    async def db_get_order_by_id(self, *, order_id: int) -> Order | None:
        result = await self.session.execute(select(Order).where(Order.id == order_id))
        return result.scalar_one_or_none()

    async def db_get_orders(self) -> List[Order]:
        result = await self.session.execute(select(Order).order_by(Order.id))
        return list(result.scalars().all())

    async def db_delete_order_by_id(self, *, order_id: int) -> bool:
        result = await self.session.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if order is None:
            return False

        await self.session.delete(order)
        return True
