from api.dependencies.services import get_message_queue_service
from fastapi import FastAPI, Request


def test_get_message_queue_service() -> None:
    app = FastAPI()
    mq_service = object()
    app.state.message_queue_service = mq_service

    request = Request(
        scope={
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "app": app,
        }
    )

    result = get_message_queue_service(request)

    assert result is mq_service
