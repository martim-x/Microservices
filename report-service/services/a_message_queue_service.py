import asyncio
import json
import logging
from random import random

import aio_pika
from aio_pika.abc import (
    AbstractChannel,
    AbstractIncomingMessage,
    AbstractQueue,
)
from api.settings import settings
from database.schemas import ReportCreate

logger = logging.getLogger("uvicorn.error")


class AMessageQueueService:
    def __init__(
        self,
        channel: AbstractChannel,
        routing_key: str = "report.generate",
        routing_key_error: str = "report.generate.error",
    ) -> None:
        self.channel = channel
        self._routing_key = routing_key
        self._error_routing_key = routing_key_error
        self.max_retries = int(settings.RABBITMQ_MAX_RETRIES)

        self._queue: AbstractQueue | None = None
        self._consumer_tag: str | None = None

    async def start(self) -> None:
        self._queue = await self.channel.declare_queue(
            self._routing_key,
            durable=True,
        )
        await self.channel.declare_queue(
            self._error_routing_key,
            durable=True,
        )

        self._consumer_tag = await self._queue.consume(self._consume_message)
        logger.info("Consumer started for queue %s", self._routing_key)

    async def stop(self) -> None:
        if self._queue is not None and self._consumer_tag is not None:
            await self._queue.cancel(self._consumer_tag)
            self._consumer_tag = None
            logger.info("Consumer stopped for queue %s", self._routing_key)

    async def _generate_report(
        self,
        *,
        report: ReportCreate,
    ) -> None:
        logger.info(
            "Создан отчет для заказа %s, user_id=%s, total=%s",
            report.order_id,
            report.user_id,
            report.total,
        )

    async def _publish_retry(
        self,
        *,
        body: bytes,
        retry_count: int,
    ) -> None:
        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=body,
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                headers={"x-retry-count": retry_count},
            ),
            routing_key=self._routing_key,
        )

    async def _publish_error(
        self,
        *,
        body: bytes,
        retry_count: int,
        error: str,
    ) -> None:
        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=body,
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                headers={
                    "x-retry-count": retry_count,
                    "x-error": error,
                },
            ),
            routing_key=self._error_routing_key,
        )

    async def _consume_message(
        self,
        message: AbstractIncomingMessage,
    ) -> None:
        retry_count = 0

        try:
            if message.headers:
                retry_count = int(message.headers.get("x-retry-count", 0))

            payload = json.loads(message.body.decode("utf-8"))
            report = ReportCreate.model_validate(payload)

            await self._generate_report(report=report)
            if round(random()):
                raise Exception("Упс... Произошла ошибка")
            await message.ack()

            logger.info("Сообщение успешно обработано")

        except Exception as e:
            retry_count += 1

            if retry_count <= self.max_retries:
                delay = retry_count**2

                logger.warning(
                    "Ошибка обработки. Retry %s/%s через %s сек. Ошибка: %s",
                    retry_count,
                    self.max_retries,
                    delay,
                    e,
                )

                await asyncio.sleep(delay)

                await self._publish_retry(
                    body=message.body,
                    retry_count=retry_count,
                )
                await message.ack()
            else:
                logger.exception(
                    "Лимит retry исчерпан. Сообщение отправляется в error queue: %s",
                    e,
                )

                await self._publish_error(
                    body=message.body,
                    retry_count=retry_count,
                    error=str(e),
                )
                await message.ack()
