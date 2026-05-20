import json
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from database.schemas import ReportCreate
from services.a_message_queue_service import AMessageQueueService


@pytest.mark.asyncio
async def test_produce_report_publishes_message() -> None:
    published: dict[str, object] = {}

    async def fake_publish(message: object, routing_key: str) -> None:
        published["message"] = message
        published["routing_key"] = routing_key

    channel = AsyncMock()
    channel.default_exchange = SimpleNamespace(publish=fake_publish)

    service = AMessageQueueService(
        channel=channel,
        routing_key="test.route",
    )

    payload = ReportCreate(
        order_id=1,
        user_id=2,
        total=Decimal("10.50"),
    )

    await service.produce_report(payload)

    assert published["routing_key"] == "test.route"

    message = cast(Any, published["message"])
    body = json.loads(message.body.decode("utf-8"))
    assert body["order_id"] == 1
    assert body["user_id"] == 2
    assert body["total"] == "10.50"
    assert message.content_type == "application/json"


def test_message_queue_service_init() -> None:
    channel = AsyncMock()

    service = AMessageQueueService(
        channel=channel,
        routing_key="reports.generate",
    )

    assert service._routing_key == "reports.generate"
