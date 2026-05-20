from collections.abc import Callable

import pytest
from services.exceptions import (
    BadRequestError,
    ConflictError,
    ExternalServiceError,
    ExternalServiceUnavailableError,
    ForbiddenError,
    GoneError,
    NotFoundError,
    ServiceError,
    UnauthorizedError,
    ValidationServiceError,
)


def test_service_error_str() -> None:
    error = ServiceError(status_code=418, detail="teapot")
    assert str(error) == "418: teapot"


@pytest.mark.parametrize(
    "error_factory,status_code,detail",
    [
        pytest.param(BadRequestError, 400, "Некорректный запрос", id="bad-request"),
        pytest.param(
            UnauthorizedError,
            401,
            "Необходима аутентификация",
            id="unauthorized",
        ),
        pytest.param(ForbiddenError, 403, "Недостаточно прав", id="forbidden"),
        pytest.param(NotFoundError, 404, "Ресурс не найден", id="not-found"),
        pytest.param(ConflictError, 409, "Конфликт данных", id="conflict"),
        pytest.param(GoneError, 410, "Ресурс более недоступен", id="gone"),
        pytest.param(
            ValidationServiceError,
            422,
            "Ошибка валидации данных",
            id="validation",
        ),
        pytest.param(
            ExternalServiceError,
            502,
            "Ошибка внешнего сервиса",
            id="external",
        ),
        pytest.param(
            ExternalServiceUnavailableError,
            503,
            "Внешний сервис недоступен",
            id="external-unavailable",
        ),
    ],
)
def test_custom_exceptions_defaults(
    error_factory: Callable[[], ServiceError],
    status_code: int,
    detail: str,
) -> None:
    error = error_factory()

    assert error.status_code == status_code
    assert error.detail == detail
    assert str(error) == f"{status_code}: {detail}"
