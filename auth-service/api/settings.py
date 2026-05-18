from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            "secrets.env",
            "variables.env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ——— API ———————————————————————————————————

    API_APP: str

    # ——— JWT ———————————————————————————————————

    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_TTL: int
    REFRESH_TOKEN_TTL: int

    # ——— DB ————————————————————————————————————

    DB_DRIVENAME: str
    DB_ADMIN: str
    DB_ADMIN_PASS: str
    DB_HOST_MASTER: str
    DB_HOST_SLAVE: str
    DB_NAME: str
    DB_PORT_FROM_MASTER: int
    DB_PORT_FROM_SLAVE: int
    DB_IMAGE: str
    DB_VERSION: str
    DB_PORT_TO_MASTER: int
    DB_PORT_TO_SLAVE: int
    DB_VOLUME_MASTER: str
    DB_VOLUME_SLAVE: str
    DB_VOLUME: str

    # ——— Redis —————————————————————————————————

    REDIS_IMAGE: str
    REDIS_VERSION: str
    REDIS_HOST: str
    REDIS_PORT_FROM: int
    REDIS_PORT_TO: int
    REDIS_VOLUME: str

    # ——— RabbitMQ ——————————————————————————————

    RABBITMQ_IMAGE: str
    RABBITMQ_VERSION: str
    RABBITMQ_HOST: str
    RABBITMQ_PORT_AMQP_FROM: int
    RABBITMQ_PORT_AMQP_TO: int
    RABBITMQ_PORT_HTTP_FROM: int
    RABBITMQ_PORT_HTTP_TO: int
    RABBITMQ_DEFAULT_USER: str
    RABBITMQ_DEFAULT_PASS: str
    RABBITMQ_VOLUME: str
    RABBITMQ_MAX_RETRIES: int
    RABBITMQ_ROUTING_KEY: str
    RABBITMQ_ROUTING_KEY_ERROR: str

    # ——— ServiceToken ——————————————————————————

    SERVICE_SECRET_KEY: str
    SERVICE_ACCESS_TOKEN_TTL: int

    # ——— ServicePorts ———————————————————————————

    ORDER_SERVICE_PORT: int
    USER_PRODUCT_SERVICE_PORT: int
    AUTH_SERVICE_PORT: int
    REPORT_SERVICE_PORT: int

    # ——— ServiceHosts ———————————————————————————

    AUTH_SERVICE_HOST: str
    USER_PRODUCT_SERVICE_HOST: str
    ORDER_SERVICE_HOST: str
    REPORT_SERVICE_HOST: str

    # ——— ServiceNames ——————————————————————————

    AUTH_SERVICE_NAME: str
    USER_PRODUCT_SERVICE_NAME: str
    ORDER_SERVICE_NAME: str
    REPORT_SERVICE_NAME: str

    # ——— ServiceVersions ———————————————————————

    AUTH_SERVICE_VERSION: str
    USER_PRODUCT_SERVICE_VERSION: str
    ORDER_SERVICE_VERSION: str
    REPORT_SERVICE_VERSION: str

    # ——— Computed URLs —————————————————————————

    @computed_field  # type: ignore[prop-decorator]
    def DB_MASTER_URL(self) -> URL:
        return URL.create(
            drivername=self.DB_DRIVENAME,
            username=self.DB_ADMIN,
            password=self.DB_ADMIN_PASS,
            host=self.DB_HOST_MASTER,
            port=self.DB_PORT_TO_MASTER,
            database=self.DB_NAME,
        )

    @computed_field  # type: ignore[prop-decorator]
    def DB_SLAVE_URL(self) -> URL:
        return URL.create(
            drivername=self.DB_DRIVENAME,
            username=self.DB_ADMIN,
            password=self.DB_ADMIN_PASS,
            host=self.DB_HOST_SLAVE,
            port=self.DB_PORT_TO_SLAVE,
            database=self.DB_NAME,
        )

    # ——— SERVICES ——————————————————————————————————

    @computed_field  # type: ignore[prop-decorator]
    def POSTGRESQL_DSN(self) -> str:
        return (
            f"postgresql://{self.DB_ADMIN}:{self.DB_ADMIN_PASS}"
            f"@{self.DB_HOST_SLAVE}:{self.DB_PORT_TO_SLAVE}/{self.DB_NAME}"
        )

    @computed_field  # type: ignore[prop-decorator]
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT_TO}"

    @computed_field  # type: ignore[prop-decorator]
    def RABBITMQ_URL(self) -> str:
        return (
            f"amqp://{self.RABBITMQ_DEFAULT_USER}:{self.RABBITMQ_DEFAULT_PASS}"
            f"@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT_AMQP_TO}/"
        )

    @computed_field  # type: ignore[prop-decorator]
    def POSTGRESQL_REPLICATION_URL(self) -> str:
        return (
            f"host={self.DB_HOST_MASTER} "
            f"port={self.DB_PORT_TO_MASTER} "
            f"dbname={self.DB_NAME} "
            f"user=repl_user "
            f"password={self.DB_ADMIN_PASS}"
        )

    # ——— SERVICE URLS ——————————————————————————————

    @computed_field  # type: ignore[prop-decorator]
    def USER_PRODUCT_SERVICE_URL(self) -> str:
        return (
            f"http://{self.USER_PRODUCT_SERVICE_HOST}:"
            f"{self.USER_PRODUCT_SERVICE_PORT}/api"
        )

    @computed_field  # type: ignore[prop-decorator]
    def ORDER_SERVICE_URL(self) -> str:
        return f"http://{self.ORDER_SERVICE_HOST}:" f"{self.ORDER_SERVICE_PORT}/api"

    @computed_field  # type: ignore[prop-decorator]
    def AUTH_SERVICE_URL(self) -> str:
        return f"http://{self.AUTH_SERVICE_HOST}:" f"{self.AUTH_SERVICE_PORT}/api"

    @computed_field  # type: ignore[prop-decorator]
    def REPORT_SERVICE_URL(self) -> str:
        return f"http://{self.REPORT_SERVICE_HOST}:" f"{self.REPORT_SERVICE_PORT}/api"

    # ——— DB, CACHE, MQ —————————————————————————

    @computed_field  # type: ignore[prop-decorator]
    def DB_SERVICE_NAME(self) -> str:
        return "-".join([self.DB_IMAGE, self.DB_VERSION])

    @computed_field  # type: ignore[prop-decorator]
    def CACHE_SERVICE_NAME(self) -> str:
        return "-".join([self.REDIS_IMAGE, self.REDIS_VERSION])

    @computed_field  # type: ignore[prop-decorator]
    def MQ_SERVICE_NAME(self) -> str:
        return "-".join([self.RABBITMQ_IMAGE, self.RABBITMQ_VERSION])


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
