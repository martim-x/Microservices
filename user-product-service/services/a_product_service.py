from database.schemas import ProductCreate, ProductOut, ProductUpdate
from repository.a_product_repository import AProductRepository
from services.exceptions import NotFoundError


class AProductService:
    def __init__(self, product_repository: AProductRepository):
        self.product_repository = product_repository

    async def create_product(self, *, new_product: ProductCreate) -> ProductOut:
        try:
            product = await self.product_repository.db_create_product(
                name=new_product.name,
                price=new_product.price,
                quantity=new_product.quantity,
            )

            await self.product_repository.session.commit()
            return ProductOut.model_validate(product)
        except Exception:
            await self.product_repository.session.rollback()
            raise

    async def get_product_by_id(self, *, product_id: int) -> ProductOut:
        try:
            product = await self.product_repository.db_get_product_by_id(
                product_id=product_id
            )
            if product is None:
                raise NotFoundError("Товар не найден")

            await self.product_repository.session.commit()
            return ProductOut.model_validate(product)
        except Exception:
            await self.product_repository.session.rollback()
            raise

    async def get_products(self) -> list[ProductOut]:
        try:
            products = await self.product_repository.db_get_products()
            await self.product_repository.session.commit()
            return [ProductOut.model_validate(product) for product in products]
        except Exception:
            await self.product_repository.session.rollback()
            raise

    async def update_product(
        self,
        *,
        product_id: int,
        new_product: ProductUpdate,
    ) -> ProductOut:
        try:
            product = await self.product_repository.db_update_product(
                product_id=product_id,
                name=new_product.name,
                price=new_product.price,
                quantity=new_product.quantity,
            )
            if product is None:
                raise NotFoundError("Товар не найден")

            await self.product_repository.session.commit()
            return ProductOut.model_validate(product)
        except Exception:
            await self.product_repository.session.rollback()
            raise

    async def delete_product_by_id(self, *, product_id: int) -> bool:
        try:
            deleted = await self.product_repository.db_delete_product_by_id(
                product_id=product_id
            )
            if not deleted:
                raise NotFoundError("Товар не найден")

            await self.product_repository.session.commit()
            return True
        except Exception:
            await self.product_repository.session.rollback()
            raise
