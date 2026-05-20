import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from services.a_message_queue_service import AMessageQueueService


def test_message_queue_service_init() -> None:
    channel = AsyncMock()

    service = AMessageQueueService(
        channel=channel,
        routing_key="report.generate",
        routing_key_error="report.generate.error",
    )

    assert service.channel is channel
    assert service._routing_key == "report.generate"
    assert service._error_routing_key == "report.generate.error"
    assert isinstance(service.generated_reports, list)


@pytest.mark.asyncio
async def test_start() -> None:
    queue = AsyncMock()
    queue.consume.return_value = "consumer-tag"

    channel = AsyncMock()
    channel.declare_queue.side_effect = [queue, AsyncMock()]

    service = AMessageQueueService(
        channel=channel,
        routing_key="report.generate",
        routing_key_error="report.generate.error",
    )

    await service.start()

    assert service._queue is queue
    assert service._consumer_tag == "consumer-tag"
    assert channel.declare_queue.await_count == 2


@pytest.mark.asyncio
async def test_stop() -> None:
    queue = AsyncMock()

    channel = AsyncMock()
    service = AMessageQueueService(channel=channel)
    service._queue = queue
    service._consumer_tag = "consumer-tag"

    await service.stop()

    queue.cancel.assert_awaited_once_with("consumer-tag")
    assert service._consumer_tag is None


@pytest.mark.asyncio
async def test_publish_retry() -> None:
    published: dict[str, object] = {}

    async def fake_publish(message: object, routing_key: str) -> None:
        published["message"] = message
        published["routing_key"] = routing_key

    channel = AsyncMock()
    channel.default_exchange = SimpleNamespace(publish=fake_publish)

    service = AMessageQueueService(
        channel=channel,
        routing_key="report.generate",
    )

    await service._publish_retry(
        body=b'{"order_id":1,"user_id":2,"total":"10.50"}',
        retry_count=2,
    )

    assert published["routing_key"] == "report.generate"
    message = published["message"]
    assert getattr(message, "headers")["x-retry-count"] == 2


@pytest.mark.asyncio
async def test_publish_error() -> None:
    published: dict[str, object] = {}

    async def fake_publish(message: object, routing_key: str) -> None:
        published["message"] = message
        published["routing_key"] = routing_key

    channel = AsyncMock()
    channel.default_exchange = SimpleNamespace(publish=fake_publish)

    service = AMessageQueueService(
        channel=channel,
        routing_key_error="report.generate.error",
    )

    await service._publish_error(
        body=b'{"order_id":1,"user_id":2,"total":"10.50"}',
        retry_count=3,
        error="boom",
    )

    assert published["routing_key"] == "report.generate.error"
    message = published["message"]
    assert getattr(message, "headers")["x-retry-count"] == 3
    assert getattr(message, "headers")["x-error"] == "boom"


@pytest.mark.asyncio
async def test_consume_message_success(monkeypatch: pytest.MonkeyPatch) -> None:
    channel = AsyncMock()
    service = AMessageQueueService(channel=channel)

    generate_report_mock = AsyncMock()
    monkeypatch.setattr(service, "_generate_report", generate_report_mock)
    monkeypatch.setattr("services.a_message_queue_service.random", lambda: 0.0)

    message = AsyncMock()
    message.body = json.dumps({"order_id": 1, "user_id": 2, "total": "10.50"}).encode(
        "utf-8"
    )
    message.headers = {}

    await service._consume_message(message)

    message.ack.assert_awaited_once()
    assert len(service.generated_reports) == 1
    assert service.generated_reports[0].order_id == 1


@pytest.mark.asyncio
async def test_consume_message_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    channel = AsyncMock()
    service = AMessageQueueService(channel=channel)

    monkeypatch.setattr(service, "_generate_report", AsyncMock())
    publish_retry_mock = AsyncMock()
    monkeypatch.setattr(service, "_publish_retry", publish_retry_mock)
    service.max_retries = 3

    monkeypatch.setattr("services.a_message_queue_service.random", lambda: 1.0)
    monkeypatch.setattr(
        "services.a_message_queue_service.asyncio.sleep",
        AsyncMock(),
    )

    message = AsyncMock()
    message.body = json.dumps({"order_id": 1, "user_id": 2, "total": "10.50"}).encode(
        "utf-8"
    )
    message.headers = {}

    await service._consume_message(message)

    publish_retry_mock.assert_awaited_once()
    message.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_consume_message_goes_to_error_queue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channel = AsyncMock()
    service = AMessageQueueService(channel=channel)

    monkeypatch.setattr(
        service,
        "_generate_report",
        AsyncMock(side_effect=Exception("fail")),
    )
    publish_error_mock = AsyncMock()
    monkeypatch.setattr(service, "_publish_error", publish_error_mock)
    service.max_retries = 0

    message = AsyncMock()
    message.body = json.dumps({"order_id": 1, "user_id": 2, "total": "10.50"}).encode(
        "utf-8"
    )
    message.headers = {}

    await service._consume_message(message)

    publish_error_mock.assert_awaited_once()
    message.ack.assert_awaited_once()
