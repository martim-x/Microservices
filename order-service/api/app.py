import logging
import time
from contextlib import asynccontextmanager

import aio_pika
import redis.asyncio as aioredis
from api.dependencies.limiter import rate_limit_handler
from api.health.core import health_router
from api.settings import settings
from api.v1.core import v1_router
from api.v2.core import v2_router
from database.connection import SessionLocalMaster
from database.schemas import (
    ServiceTokenCreate,
)
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from repository.a_service_token_repository import AServiceTokenRepository
from services.a_message_queue_service import AMessageQueueService
from services.a_service_token_service import AServiceTokenService
from services.exceptions import ServiceError
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger("uvicorn.error")


# ——— Lifespan ————————————————————————————————————————————————————————————————


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis_client = await aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
    )

    app.state.rabbitmq_connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    app.state.rabbitmq_channel = await app.state.rabbitmq_connection.channel()
    await app.state.rabbitmq_channel.set_qos(prefetch_count=1)

    await app.state.rabbitmq_channel.declare_queue(
        name=settings.RABBITMQ_ROUTING_KEY,
        durable=True,
    )

    app.state.message_queue_service = AMessageQueueService(
        channel=app.state.rabbitmq_channel,
        routing_key=settings.RABBITMQ_ROUTING_KEY,
    )

    app.state.services = {}
    app.state.services["health"] = {
        "startup_complete": False,
        "shutdown_requested": False,
        "checks": {
            settings.DB_SERVICE_NAME: {
                "ok": False,
                "required": True,
                "message": None,
            },
            settings.CACHE_SERVICE_NAME: {
                "ok": False,
                "required": True,
                "message": None,
            },
            settings.ORDER_SERVICE_NAME: {
                "ok": False,
                "required": True,
                "message": None,
            },
            settings.MQ_SERVICE_NAME: {
                "ok": False,
                "required": True,
                "message": None,
            },
        },
    }

    app.add_exception_handler(
        RateLimitExceeded,
        rate_limit_handler,
    )

    try:
        async with SessionLocalMaster() as session:
            repo = AServiceTokenRepository(session=session)
            service = AServiceTokenService(service_token_repository=repo)

            exists = await repo.db_get_service_token_by_name(
                service_name=settings.ORDER_SERVICE_NAME,
            )

            if not exists:
                await service.register_service(
                    new_service=ServiceTokenCreate(
                        service_name=settings.ORDER_SERVICE_NAME,
                        service_secret=settings.SERVICE_SECRET_KEY,
                        allowed_audience=settings.USER_PRODUCT_SERVICE_NAME,
                        allowed_scopes=["users.read", "products.read"],
                    )
                )

        app.state.services["health"]["startup_complete"] = True
        app.state.services["health"]["checks"][settings.DB_SERVICE_NAME]["ok"] = True
        app.state.services["health"]["checks"][settings.CACHE_SERVICE_NAME]["ok"] = True
        app.state.services["health"]["checks"][settings.ORDER_SERVICE_NAME]["ok"] = True
        app.state.services["health"]["checks"][settings.MQ_SERVICE_NAME]["ok"] = True

        yield

    finally:
        app.state.services["health"]["shutdown_requested"] = True

        if not app.state.rabbitmq_channel.is_closed:
            await app.state.rabbitmq_channel.close()
        if not app.state.rabbitmq_connection.is_closed:
            await app.state.rabbitmq_connection.close()
        await app.state.redis_client.close()


# ——— App —————————————————————————————————————————————————————————————————————


app = FastAPI(
    title=settings.ORDER_SERVICE_NAME,
    lifespan=lifespan,
    version=settings.ORDER_SERVICE_VERSION,
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


# ——— Routers ——————————————————————————————————————————————————————————————————


for router in [health_router, v1_router, v2_router]:
    app.include_router(router)
