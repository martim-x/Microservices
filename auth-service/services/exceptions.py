from dataclasses import dataclass


@dataclass
class ServiceError(Exception):
    status_code: int
    detail: str

    def __str__(self) -> str:
        return f"{self.status_code}: {self.detail}"


class BadRequestError(ServiceError):
    def __init__(self, detail: str = "Некорректный запрос") -> None:
        super().__init__(400, detail)


class UnauthorizedError(ServiceError):
    def __init__(self, detail: str = "Необходима аутентификация") -> None:
        super().__init__(401, detail)


class ForbiddenError(ServiceError):
    def __init__(self, detail: str = "Недостаточно прав") -> None:
        super().__init__(403, detail)


class NotFoundError(ServiceError):
    def __init__(self, detail: str = "Ресурс не найден") -> None:
        super().__init__(404, detail)


class ConflictError(ServiceError):
    def __init__(self, detail: str = "Конфликт данных") -> None:
        super().__init__(409, detail)


class GoneError(ServiceError):
    def __init__(self, detail: str = "Ресурс более недоступен") -> None:
        super().__init__(410, detail)


class ExternalServiceError(ServiceError):
    def __init__(self, detail: str = "Ошибка внешнего сервиса") -> None:
        super().__init__(502, detail)


class ExternalServiceUnavailableError(ServiceError):
    def __init__(self, detail: str = "Внешний сервис недоступен") -> None:
        super().__init__(503, detail)


class ValidationServiceError(ServiceError):
    def __init__(self, detail: str = "Ошибка валидации данных") -> None:
        super().__init__(422, detail)
