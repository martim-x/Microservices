import logging
import time
from contextlib import asynccontextmanager

from api.settings import settings
from database.connection import SessionLocalMaster, get_write_session
from database.schemas import ServiceAccessTokenPayload, ServiceTokenCreate
from fastapi import APIRouter, Depends, FastAPI, Request, Response
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from repository.a_auth_repository import AAuthRepository
from repository.a_service_token_repository import AServiceTokenRepository
from services.a_auth_service import AAuthService
from services.a_service_token_service import AServiceTokenService
from services.exceptions import ServiceError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

logger = logging.getLogger("uvicorn.error")
limiter = Limiter(key_func=get_remote_address)


# ——— Lifespan ————————————————————————————————————————————————————————————————


@asynccontextmanager
async def lifespan(app: FastAPI):
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
            settings.AUTH_SERVICE_NAME: {
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
                service_name=settings.AUTH_SERVICE_NAME,
            )

            if not exists:
                await service.register_service(
                    new_service=ServiceTokenCreate(
                        service_name=settings.AUTH_SERVICE_NAME,
                        service_secret=settings.SERVICE_SECRET_KEY,
                        allowed_audience=settings.USER_PRODUCT_SERVICE_NAME,
                        allowed_scopes=["users.read", "users.create"],
                    )
                )

        app.state.services["health"]["startup_complete"] = True
        app.state.services["health"]["checks"][settings.DB_SERVICE_NAME]["ok"] = True
        app.state.services["health"]["checks"][settings.AUTH_SERVICE_NAME]["ok"] = True
        yield
    finally:
        app.state.services["health"]["shutdown_requested"] = True


# ——— App —————————————————————————————————————————————————————————————————————


app = FastAPI(
    title=settings.AUTH_SERVICE_NAME,
    lifespan=lifespan,
    version=settings.AUTH_SERVICE_VERSION,
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


# ——— DI: auth ————————————————————————————————————————————————————————————————


async def get_auth_repository(
    session=Depends(get_write_session),
) -> AAuthRepository:
    return AAuthRepository(session=session)


async def get_auth_service(
    auth_repo: AAuthRepository = Depends(get_auth_repository),
) -> AAuthService:
    return AAuthService(
        auth_repository=auth_repo,
    )


# ——— Security ————————————————————————————————————————————————————————————————


security = HTTPBearer()


async def get_service_token_repository(
    session=Depends(get_write_session),
) -> AServiceTokenRepository:
    return AServiceTokenRepository(session=session)


async def get_service_token_service(
    service_token_repository: AServiceTokenRepository = Depends(
        get_service_token_repository
    ),
) -> AServiceTokenService:
    return AServiceTokenService(service_token_repository=service_token_repository)


async def get_current_service(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    service_token_service: AServiceTokenService = Depends(get_service_token_service),
) -> ServiceAccessTokenPayload:
    return service_token_service.verify_service_access_token(
        service_access_token=credentials.credentials,
        expected_audience=settings.AUTH_SERVICE_NAME,
    )


# ——— Routers ——————————————————————————————————————————————————————————————————


auth_router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
)

health_router = APIRouter(
    prefix="/api/health",
    tags=["health"],
)


import api.auth.auth
import api.health.health

for router in [auth_router, health_router]:
    app.include_router(router)
