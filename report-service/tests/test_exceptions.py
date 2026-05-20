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
    err = ServiceError(status_code=418, detail="boom")
    assert str(err) == "418: boom"


def test_bad_request_error() -> None:
    err = BadRequestError()
    assert err.status_code == 400
    assert err.detail == "Некорректный запрос"


def test_unauthorized_error() -> None:
    err = UnauthorizedError()
    assert err.status_code == 401
    assert err.detail == "Необходима аутентификация"


def test_forbidden_error() -> None:
    err = ForbiddenError()
    assert err.status_code == 403
    assert err.detail == "Недостаточно прав"


def test_not_found_error() -> None:
    err = NotFoundError()
    assert err.status_code == 404
    assert err.detail == "Ресурс не найден"


def test_conflict_error() -> None:
    err = ConflictError()
    assert err.status_code == 409
    assert err.detail == "Конфликт данных"


def test_gone_error() -> None:
    err = GoneError()
    assert err.status_code == 410
    assert err.detail == "Ресурс более недоступен"


def test_external_service_error() -> None:
    err = ExternalServiceError()
    assert err.status_code == 502
    assert err.detail == "Ошибка внешнего сервиса"


def test_external_service_unavailable_error() -> None:
    err = ExternalServiceUnavailableError()
    assert err.status_code == 503
    assert err.detail == "Внешний сервис недоступен"


def test_validation_service_error() -> None:
    err = ValidationServiceError()
    assert err.status_code == 422
    assert err.detail == "Ошибка валидации данных"
