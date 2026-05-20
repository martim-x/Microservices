import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

TEST_ENV = {
    "API_APP": "api.app:app",
    "SECRET_KEY": "test-secret-key",
    "ALGORITHM": "HS256",
    "ACCESS_TOKEN_TTL": "15",
    "REFRESH_TOKEN_TTL": "30",
    "DB_DRIVENAME": "postgresql+asyncpg",
    "DB_ADMIN_MASTER": "postgres",
    "DB_ADMIN_PASS_MASTER": "postgres",
    "DB_HOST_MASTER": "localhost",
    "DB_PORT_FROM_MASTER": "5432",
    "DB_PORT_TO_MASTER": "5432",
    "DB_ADMIN_SLAVE": "postgres",
    "DB_ADMIN_PASS_SLAVE": "postgres",
    "DB_HOST_SLAVE": "localhost",
    "DB_PORT_FROM_SLAVE": "5433",
    "DB_PORT_TO_SLAVE": "5433",
    "DB_NAME": "test_db",
    "DB_IMAGE": "postgres",
    "DB_VERSION": "16",
    "DB_VOLUME_MASTER": "pg_master_data",
    "DB_VOLUME_SLAVE": "pg_slave_data",
    "DB_VOLUME": "pg_data",
    "REPL_USER": "repl_user",
    "REPL_PASSWORD": "repl_password",
    "REDIS_IMAGE": "redis",
    "REDIS_VERSION": "7",
    "REDIS_VOLUME": "redis_data",
    "REDIS_URL": "redis://localhost:6379/0",
    "RABBITMQ_IMAGE": "rabbitmq",
    "RABBITMQ_VERSION": "3-management",
    "RABBITMQ_HOST": "localhost",
    "RABBITMQ_PORT_AMQP_FROM": "5672",
    "RABBITMQ_PORT_AMQP_TO": "5672",
    "RABBITMQ_PORT_HTTP_FROM": "15672",
    "RABBITMQ_PORT_HTTP_TO": "15672",
    "RABBITMQ_DEFAULT_USER": "guest",
    "RABBITMQ_DEFAULT_PASS": "guest",
    "RABBITMQ_VOLUME": "rabbitmq_data",
    "RABBITMQ_MAX_RETRIES": "3",
    "RABBITMQ_ROUTING_KEY": "test.key",
    "RABBITMQ_ROUTING_KEY_ERROR": "test.key.error",
    "SERVICE_SECRET_KEY": "super-secret-service-key",
    "SERVICE_ACCESS_TOKEN_TTL": "15",
    "ORDER_SERVICE_PORT": "8001",
    "USER_PRODUCT_SERVICE_PORT": "8002",
    "AUTH_SERVICE_PORT": "8003",
    "REPORT_SERVICE_PORT": "8004",
    "AUTH_SERVICE_HOST": "localhost",
    "USER_PRODUCT_SERVICE_HOST": "localhost",
    "ORDER_SERVICE_HOST": "localhost",
    "REPORT_SERVICE_HOST": "localhost",
    "AUTH_SERVICE_NAME": "auth-service",
    "USER_PRODUCT_SERVICE_NAME": "user-product-service",
    "ORDER_SERVICE_NAME": "order-service",
    "REPORT_SERVICE_NAME": "report-service",
    "AUTH_SERVICE_VERSION": "v1",
    "USER_PRODUCT_SERVICE_VERSION": "v1",
    "ORDER_SERVICE_VERSION": "v1",
    "REPORT_SERVICE_VERSION": "v1",
}


for key, value in TEST_ENV.items():
    os.environ.setdefault(key, value)


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def app() -> FastAPI:
    from api.app import app as fastapi_app

    return fastapi_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)
