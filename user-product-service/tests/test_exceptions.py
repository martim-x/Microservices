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
    err = BadRequestError("bad")
    assert err.status_code == 400
    assert err.detail == "bad"


def test_unauthorized_error() -> None:
    err = UnauthorizedError("unauth")
    assert err.status_code == 401
    assert err.detail == "unauth"


def test_forbidden_error() -> None:
    err = ForbiddenError("forbidden")
    assert err.status_code == 403
    assert err.detail == "forbidden"


def test_not_found_error() -> None:
    err = NotFoundError("missing")
    assert err.status_code == 404
    assert err.detail == "missing"


def test_conflict_error() -> None:
    err = ConflictError("conflict")
    assert err.status_code == 409
    assert err.detail == "conflict"


def test_gone_error() -> None:
    err = GoneError("gone")
    assert err.status_code == 410
    assert err.detail == "gone"


def test_external_service_error() -> None:
    err = ExternalServiceError("external")
    assert err.status_code == 502
    assert err.detail == "external"


def test_external_service_unavailable_error() -> None:
    err = ExternalServiceUnavailableError("unavailable")
    assert err.status_code == 503
    assert err.detail == "unavailable"


def test_validation_service_error() -> None:
    err = ValidationServiceError("validation")
    assert err.status_code == 422
    assert err.detail == "validation"
