import asyncio

import httpx
from services.exceptions import (
    ExternalServiceError,
    ExternalServiceUnavailableError,
    ValidationServiceError,
)


class AExchangeService:
    def __init__(self) -> None:
        self.attemps = 5
        self.timeout = 5.0
        # только имя и base_url
        self.providers = (
            {
                "name": "frankfurter",
                "base_url": "https://api.frankfurter.dev/v1",
            },
            {
                "name": "exchange-rate-api",
                "base_url": "https://api.exchangerate-api.com/v4/latest",
            },
        )

    @staticmethod
    def _normalize_currency(currency: str) -> str:
        currency = currency.strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ValidationServiceError(
                "Код валюты должен состоять из 3 латинских букв"
            )
        return currency

    async def _fetch_from_provider(
        self,
        provider: dict,
        *,
        from_currency: str,
        to_currency: str,
    ) -> tuple[str, float]:
        name = provider["name"]
        base_url = provider["base_url"]

        if name == "frankfurter":
            path = f"/latest?base={from_currency}&symbols={to_currency}"
        elif name == "exchange-rate-api":
            path = f"/{from_currency}"
        else:
            raise ExternalServiceError(f"Неизвестный провайдер курсов: {name}")

        last_error: Exception | None = None

        async with httpx.AsyncClient(
            base_url=base_url,
            timeout=self.timeout,
        ) as client:
            for attempt in range(1, self.attemps + 1):
                try:
                    response = await client.get(path)
                    response.raise_for_status()
                    data = response.json()
                    break

                except httpx.HTTPStatusError as exc:
                    status_code = exc.response.status_code

                    if 400 <= status_code < 500:
                        raise ExternalServiceError(
                            f"Сервис {name} вернул ошибку клиента: {status_code}"
                        ) from exc

                    last_error = exc

                except (httpx.TimeoutException, httpx.RequestError) as exc:
                    last_error = exc

                if attempt < self.attemps:
                    await asyncio.sleep(attempt)

            else:
                raise ExternalServiceUnavailableError(
                    f"Сервис {name} недоступен после {self.attemps} попыток"
                ) from last_error

        rates = data.get("rates")
        if not isinstance(rates, dict):
            raise ExternalServiceError(f"{name} вернул некорректный формат ответа")

        rate = rates.get(to_currency)
        if rate is None:
            raise ValidationServiceError(
                f"{name} не вернул курс {from_currency} -> {to_currency}"
            )

        try:
            return name, float(rate)
        except (TypeError, ValueError) as exc:
            raise ExternalServiceError(
                f"{name} вернул некорректное значение курса"
            ) from exc

    async def _get_exchange_rate(
        self,
        *,
        from_currency: str,
        to_currency: str,
    ) -> tuple[str, float]:
        from_currency = self._normalize_currency(from_currency)
        to_currency = self._normalize_currency(to_currency)

        tasks = [
            asyncio.create_task(
                self._fetch_from_provider(
                    provider,
                    from_currency=from_currency,
                    to_currency=to_currency,
                )
            )
            for provider in self.providers
        ]

        errors: list[Exception] = []

        try:
            while tasks:
                done, pending = await asyncio.wait(
                    tasks,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                for task in done:
                    try:
                        provider_name, rate = task.result()
                        for p in pending:
                            p.cancel()
                        await asyncio.gather(*pending, return_exceptions=True)
                        return provider_name, rate
                    except Exception as exc:
                        errors.append(exc)

                tasks = list(pending)
        finally:
            for t in tasks:
                t.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        if errors:
            for error in errors:
                if isinstance(
                    error,
                    (
                        ValidationServiceError,
                        ExternalServiceError,
                        ExternalServiceUnavailableError,
                    ),
                ):
                    raise error
            raise errors[0]

        raise ExternalServiceUnavailableError(
            "Ни один сервис курсов валют не вернул успешный результат"
        )

    async def convert_price(
        self,
        *,
        price: float,
        from_currency: str,
        to_currency: str,
    ) -> dict:
        if price < 0:
            raise ValidationServiceError("Цена не может быть отрицательной")

        from_currency = self._normalize_currency(from_currency)
        to_currency = self._normalize_currency(to_currency)

        if from_currency == to_currency:
            return {
                "provider": "local",
                "rate": 1.0,
                "converted_price": price,
                "from_currency": from_currency,
                "to_currency": to_currency,
            }

        provider, rate = await self._get_exchange_rate(
            from_currency=from_currency,
            to_currency=to_currency,
        )

        return {
            "provider": provider,
            "rate": rate,
            "converted_price": price * rate,
            "from_currency": from_currency,
            "to_currency": to_currency,
        }
