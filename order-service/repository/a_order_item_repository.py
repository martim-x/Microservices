from decimal import Decimal
from typing import List

from database.models import OrderItem
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class AOrderItemRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def db_create_order_item(
        self,
        *,
        order_id: int,
        product_id: int,
        quantity: int,
        price: Decimal,
    ) -> OrderItem:
        order_item = OrderItem(
            order_id=order_id,
            product_id=product_id,
            quantity=quantity,
            price=price,
        )
        self.session.add(order_item)
        await self.session.flush()
        await self.session.refresh(order_item)
        return order_item

    async def db_get_order_item_by_id(
        self,
        *,
        order_item_id: int,
    ) -> OrderItem | None:
        result = await self.session.execute(
            select(OrderItem).where(OrderItem.id == order_item_id)
        )
        return result.scalar_one_or_none()

    async def db_get_order_items(self) -> List[OrderItem]:
        result = await self.session.execute(select(OrderItem).order_by(OrderItem.id))
        return list(result.scalars().all())

    async def db_delete_order_item_by_id(
        self,
        *,
        order_item_id: int,
    ) -> bool:
        result = await self.session.execute(
            select(OrderItem).where(OrderItem.id == order_item_id)
        )
        order_item = result.scalar_one_or_none()
        if order_item is None:
            return False

        await self.session.delete(order_item)
        return True
