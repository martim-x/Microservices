from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

metrics_router = APIRouter(
    prefix="/metrics",
    tags=["metrics"],
)


http_requests_total = Counter(
    name="http_requests_total",
    documentation="Общее количество HTTP запросов",
    labelnames=["method", "path", "status_code"],
)

http_request_duration_seconds = Histogram(
    name="http_request_duration_seconds",
    documentation="Время обработки запроса в секундах",
    labelnames=["method", "path"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

http_requests_in_progress = Gauge(
    name="http_requests_in_progress",
    documentation="Запросов в обработке прямо сейчас",
    labelnames=["method", "path"],
)


@metrics_router.get(
    "/",
    include_in_schema=False,
)
async def metrics() -> Response:
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
