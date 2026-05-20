from unittest.mock import AsyncMock

import pytest
from services.exceptions import ConflictError, NotFoundError


@pytest.mark.asyncio
async def test_user_service_get_user_by_id_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services.a_user_service import AUserService

    repo = AsyncMock()
    fake_user = object()
    repo.db_get_user_by_id.return_value = fake_user

    validated = object()

    class DummyUserOut:
        @staticmethod
        def model_validate(data):
            assert data is fake_user
            return validated

    monkeypatch.setattr("services.a_user_service.UserOut", DummyUserOut)

    service = AUserService(user_repository=repo)

    result = await service.get_user_by_id(user_id=1)

    assert result is validated
    repo.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_user_service_get_user_by_id_not_found() -> None:
    from services.a_user_service import AUserService

    repo = AsyncMock()
    repo.db_get_user_by_id.return_value = None

    service = AUserService(user_repository=repo)

    with pytest.raises(NotFoundError):
        await service.get_user_by_id(user_id=1)

    repo.session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_user_service_create_user_conflict() -> None:
    from database.schemas import UserCreate
    from services.a_user_service import AUserService

    repo = AsyncMock()
    repo.db_get_user_by_email.return_value = object()

    service = AUserService(user_repository=repo)

    with pytest.raises(ConflictError):
        await service.create_user(
            new_user=UserCreate(
                name="Tim",
                email="tim@example.com",
                password="strongpass123",
            )
        )

    repo.session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_product_service_get_product_by_id_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services.a_product_service import AProductService

    repo = AsyncMock()
    fake_product = object()
    repo.db_get_product_by_id.return_value = fake_product

    validated = object()

    class DummyProductOut:
        @staticmethod
        def model_validate(data):
            assert data is fake_product
            return validated

    monkeypatch.setattr("services.a_product_service.ProductOut", DummyProductOut)

    service = AProductService(product_repository=repo)

    result = await service.get_product_by_id(product_id=1)

    assert result is validated
    repo.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_product_service_get_product_by_id_not_found() -> None:
    from services.a_product_service import AProductService

    repo = AsyncMock()
    repo.db_get_product_by_id.return_value = None

    service = AProductService(product_repository=repo)

    with pytest.raises(NotFoundError):
        await service.get_product_by_id(product_id=1)

    repo.session.rollback.assert_awaited_once()
