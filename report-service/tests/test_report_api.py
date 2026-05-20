from api.dependencies.services import get_message_queue_service
from api.report.core import report_router
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_get_reports() -> None:
    app = FastAPI()
    app.include_router(report_router)

    class DummyMessageQueueService:
        generated_reports = [
            {"order_id": 1, "user_id": 2, "total": "10.50"},
            {"order_id": 2, "user_id": 3, "total": "20.00"},
        ]

    app.dependency_overrides[get_message_queue_service] = (
        lambda: DummyMessageQueueService()
    )

    client = TestClient(app)
    response = client.get("/api/report/reports")

    assert response.status_code == 200
    assert response.json() == [
        {"order_id": 1, "user_id": 2, "total": "10.50"},
        {"order_id": 2, "user_id": 3, "total": "20.00"},
    ]

    app.dependency_overrides = {}
