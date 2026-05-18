import logging
import time
from contextlib import asynccontextmanager

import aio_pika
from api.settings import settings
from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from services.a_message_queue_service import AMessageQueueService
from services.exceptions import ServiceError

logger = logging.getLogger("uvicorn.error")


# ——— Lifespan ————————————————————————————————————————————————————————————————


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.rabbitmq_connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    app.state.rabbitmq_channel = await app.state.rabbitmq_connection.channel()
    await app.state.rabbitmq_channel.set_qos(prefetch_count=1)

    app.state.message_queue_service = AMessageQueueService(
        channel=app.state.rabbitmq_channel,
        routing_key=settings.RABBITMQ_ROUTING_KEY,
        routing_key_error=settings.RABBITMQ_ROUTING_KEY_ERROR,
    )
    await app.state.message_queue_service.start()

    app.state.services = {}
    app.state.services["health"] = {
        "startup_complete": False,
        "shutdown_requested": False,
        "checks": {
            settings.MQ_SERVICE_NAME: {
                "ok": False,
                "required": True,
                "message": None,
            },
        },
    }

    try:
        app.state.services["health"]["startup_complete"] = True
        app.state.services["health"]["checks"][settings.MQ_SERVICE_NAME]["ok"] = True
        yield
    finally:
        app.state.services["health"]["shutdown_requested"] = True

        await app.state.message_queue_service.stop()

        if not app.state.rabbitmq_channel.is_closed:
            await app.state.rabbitmq_channel.close()

        if not app.state.rabbitmq_connection.is_closed:
            await app.state.rabbitmq_connection.close()


# ——— App —————————————————————————————————————————————————————————————————————


app = FastAPI(
    title=settings.REPORT_SERVICE_NAME,
    lifespan=lifespan,
    version=settings.REPORT_SERVICE_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
        "http://localhost:8002",
        "http://127.0.0.1:8002",
        "http://localhost:30000",
        "http://127.0.0.1:30000",
        "http://localhost:30001",
        "http://127.0.0.1:30001",
        "http://localhost:30002",
        "http://127.0.0.1:30002",
        "http://localhost:30003",
        "http://127.0.0.1:30003",
    ],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


# ——— Middlewares ——————————————————————————————————————————————————————————————


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    logger.info("Запрос: %s %s", request.method, request.url.path)

    response: Response = await call_next(request)
    process_time = time.time() - start_time

    logger.info("Ответ: %s, время: %.3f сек", response.status_code, process_time)
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.middleware("http")
async def error_handler(request: Request, call_next):
    try:
        return await call_next(request)

    except ServiceError as e:
        logger.warning(
            "Service ошибка: %s %s -> %s: %s",
            request.method,
            request.url.path,
            e.status_code,
            e.detail,
        )
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail},
        )

    except HTTPException as e:
        logger.warning(
            "HTTP ошибка: %s %s -> %s: %s",
            request.method,
            request.url.path,
            e.status_code,
            e.detail,
        )
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail},
        )

    except Exception as e:
        logger.error(
            "Необработанная ошибка: %s %s -> %s",
            request.method,
            request.url.path,
            e,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Внутренняя ошибка сервера"},
        )


# ——— DI: rabbitmq ————————————————————————————————————————————————————————————

health_router = APIRouter(
    prefix="/api/health",
    tags=["health"],
)

mq_router = APIRouter(
    prefix="/api/mq",
    tags=["mq"],
)

import api.health.health
import api.routes.reports

for router in [health_router, mq_router]:
    app.include_router(router)
