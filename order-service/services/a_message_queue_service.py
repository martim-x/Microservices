import json

import aio_pika
from database.schemas import ReportCreate


class AMessageQueueService:
    def __init__(
        self,
        channel: aio_pika.abc.AbstractChannel,
        routing_key: str = "default.generate",
    ):
        self._channel = channel
        self._routing_key = routing_key

    async def produce_report(self, payload: ReportCreate) -> None:
        await self._channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(payload.model_dump(mode="json")).encode(),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=self._routing_key,
        )
