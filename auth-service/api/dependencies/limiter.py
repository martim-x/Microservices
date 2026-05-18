from fastapi import Request, Response
from slowapi import (
    Limiter,
    _rate_limit_exceeded_handler,
)
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


def rate_limit_handler(request: Request, exc: Exception) -> Response:
    return _rate_limit_exceeded_handler(request, exc)  # type: ignore[arg-type]
