import logging
import time
from contextlib import asynccontextmanager

import httpx
import redis.asyncio as aioredis
from api.settings import settings
from database.connection import SessionLocalMaster, get_read_session, get_write_session
from database.schemas import (
    AccessTokenPayload,
    ServiceAccessTokenPayload,
    ServiceTokenCreate,
)
from fastapi import APIRouter, Depends, FastAPI, Request, Response, status
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from repository.a_product_repository import AProductRepository
from repository.a_service_token_repository import AServiceTokenRepository
from repository.a_user_repository import AUserRepository
from services.a_exchange_service import AExchangeService
from services.a_product_service import AProductService
from services.a_service_token_service import AServiceTokenService
from services.a_user_service import AUserService
from services.cache.a_product_cache_service import AProductCacheService
from services.cache.a_user_cache_service import AUserCacheService
from services.exceptions import ServiceError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

logger = logging.getLogger("uvicorn.error")
limiter = Limiter(key_func=get_remote_address)


# ——— Lifespan ————————————————————————————————————————————————————————————————


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis_client = await aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
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
            settings.USER_PRODUCT_SERVICE_NAME: {
                "ok": False,
                "required": True,
                "message": None,
            },
        },
    }

    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    try:
        async with SessionLocalMaster() as session:
            repo = AServiceTokenRepository(session=session)
            service = AServiceTokenService(service_token_repository=repo)

            exists = await repo.db_get_service_token_by_name(
                service_name=settings.USER_PRODUCT_SERVICE_NAME,
            )

            if not exists:
                await service.register_service(
                    new_service=ServiceTokenCreate(
                        service_name=settings.USER_PRODUCT_SERVICE_NAME,
                        service_secret=settings.SERVICE_SECRET_KEY,
                        allowed_audience=settings.USER_PRODUCT_SERVICE_NAME,
                        allowed_scopes=[""],
                    )
                )

        app.state.services["health"]["startup_complete"] = True
        app.state.services["health"]["checks"][settings.DB_SERVICE_NAME]["ok"] = True
        app.state.services["health"]["checks"][settings.CACHE_SERVICE_NAME]["ok"] = True
        app.state.services["health"]["checks"][settings.USER_PRODUCT_SERVICE_NAME][
            "ok"
        ] = True
        yield

    finally:
        app.state.services["health"]["shutdown_requested"] = True
        await app.state.redis_client.close()


# ——— App —————————————————————————————————————————————————————————————————————


app = FastAPI(
    title=settings.USER_PRODUCT_SERVICE_NAME,
    lifespan=lifespan,
    version=settings.USER_PRODUCT_SERVICE_VERSION,
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


# ——— Helpers —————————————————————————————————————————————————————————————————


def cache_dep(ttl: int = 3600):
    def wrapper(response: Response):
        response.headers["Cache-Control"] = f"max-age={ttl}"
        return response

    return wrapper


# ——— DI: internal repositories ———————————————————————————————————————————————


async def get_service_token_repository(
    session=Depends(get_write_session),
) -> AServiceTokenRepository:
    return AServiceTokenRepository(session=session)


# ——— DI: read repositories ———————————————————————————————————————————————————


async def get_user_read_repository(
    session=Depends(get_read_session),
) -> AUserRepository:
    return AUserRepository(session=session)


async def get_product_read_repository(
    session=Depends(get_read_session),
) -> AProductRepository:
    return AProductRepository(session=session)


# ——— DI: write repositories ——————————————————————————————————————————————————


async def get_user_write_repository(
    session=Depends(get_write_session),
) -> AUserRepository:
    return AUserRepository(session=session)


async def get_product_write_repository(
    session=Depends(get_write_session),
) -> AProductRepository:
    return AProductRepository(session=session)


# ——— DI: internal services ———————————————————————————————————————————————————


async def get_service_token_service(
    service_token_repository: AServiceTokenRepository = Depends(
        get_service_token_repository
    ),
) -> AServiceTokenService:
    return AServiceTokenService(service_token_repository=service_token_repository)


# ——— DI: read services ———————————————————————————————————————————————————————


async def get_user_read_service(
    user_repo: AUserRepository = Depends(get_user_read_repository),
) -> AUserService:
    return AUserService(user_repository=user_repo)


async def get_product_read_service(
    product_repo: AProductRepository = Depends(get_product_read_repository),
) -> AProductService:
    return AProductService(product_repository=product_repo)


# ——— DI: write services ——————————————————————————————————————————————————————


async def get_user_write_service(
    user_repo: AUserRepository = Depends(get_user_write_repository),
) -> AUserService:
    return AUserService(user_repository=user_repo)


async def get_product_write_service(
    product_repo: AProductRepository = Depends(get_product_write_repository),
) -> AProductService:
    return AProductService(product_repository=product_repo)


# ——— DI: redis ———————————————————————————————————————————————————————————————


async def get_redis_client(request: Request):
    return request.app.state.redis_client


# ——— DI: cache services (v2) — read-only, slave ———————————————————————————————


async def get_user_cache_service(
    redis_client: aioredis.Redis = Depends(get_redis_client),
    user_service: AUserService = Depends(get_user_read_service),
) -> AUserCacheService:
    return AUserCacheService(
        redis_client=redis_client,
        user_service=user_service,
    )


async def get_product_cache_service(
    redis_client: aioredis.Redis = Depends(get_redis_client),
    product_service: AProductService = Depends(get_product_read_service),
) -> AProductCacheService:
    return AProductCacheService(
        redis_client=redis_client,
        product_service=product_service,
    )


# ——— DI: exchange service ————————————————————————————————————————————————————


async def get_exchange_service() -> AExchangeService:
    return AExchangeService()


# ——— Security —————————————————————————————————————————————————————————————————

security = HTTPBearer()


async def get_current_service(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    service_token_service: AServiceTokenService = Depends(get_service_token_service),
) -> ServiceAccessTokenPayload:
    token_data = service_token_service.verify_service_access_token(
        service_access_token=credentials.credentials,
        expected_audience=settings.USER_PRODUCT_SERVICE_NAME,
    )
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный service token",
        )
    return token_data


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> AccessTokenPayload:
    async with httpx.AsyncClient(base_url=settings.AUTH_SERVICE_URL) as client:
        response = await client.get(f"/auth/verify/{credentials.credentials}")

    if response.status_code == 401:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный или истёкший токен",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ошибка проверки токена",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AccessTokenPayload.model_validate(response.json())


# ——— Routers ——————————————————————————————————————————————————————————————————

exchange_router = APIRouter(
    prefix="/api/exchange",
    tags=["exchange"],
)

internal_router = APIRouter(
    prefix="/api/internal",
    tags=["internal"],
    dependencies=[Depends(get_current_service)],
)

health_router = APIRouter(
    prefix="/api/health",
    tags=["health"],
)

v1_router = APIRouter(
    prefix="/api/v1",
    tags=["v1"],
    dependencies=[Depends(get_current_user)],
)

v2_router = APIRouter(
    prefix="/api/v2",
    tags=["v2"],
    dependencies=[Depends(get_current_user)],
)


import api.exchange.exchange
import api.health.health
import api.internal.products
import api.internal.users
import api.v1.products
import api.v1.users
import api.v2.products
import api.v2.users

for router in [exchange_router, health_router, internal_router, v1_router, v2_router]:
    app.include_router(router)
