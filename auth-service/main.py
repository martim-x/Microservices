import asyncio

from api.settings import settings
from database.connection import _soft_init_dbs
from uvicorn.config import Config
from uvicorn.server import Server


async def main():
    await asyncio.gather(
        _soft_init_dbs(),
        Server(
            Config(
                app=settings.API_APP,
                host="0.0.0.0",
                port=settings.AUTH_SERVICE_PORT,
            )
        ).serve(),
    )


if __name__ == "__main__":
    asyncio.run(main())
