from decimal import Decimal
from typing import List

from database.models import Product
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class AProductRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def db_create_product(
        self,
        *,
        name: str,
        price: Decimal,
        quantity: int,
    ) -> Product:
        product = Product(
            name=name,
            price=price,
            quantity=quantity,
        )
        self.session.add(product)
        await self.session.flush()
        await self.session.refresh(product)
        return product

    async def db_get_product_by_id(self, *, product_id: int) -> Product | None:
        result = await self.session.execute(
            select(Product).where(Product.id == product_id)
        )
        return result.scalar_one_or_none()

    async def db_get_products(self) -> List[Product]:
        result = await self.session.execute(select(Product).order_by(Product.id))
        return list(result.scalars().all())

    async def db_update_product(
        self,
        *,
        product_id: int,
        name: str | None = None,
        price: Decimal | None = None,
        quantity: int | None = None,
    ) -> Product | None:
        result = await self.session.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        if product is None:
            return None

        if name is not None:
            product.name = name
        if price is not None:
            product.price = price
        if quantity is not None:
            product.quantity = quantity

        await self.session.flush()
        await self.session.refresh(product)
        return product

    async def db_delete_product_by_id(self, *, product_id: int) -> bool:
        result = await self.session.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        if product is None:
            return False

        await self.session.delete(product)
        return True
