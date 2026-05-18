import asyncio

from api.settings import settings
from uvicorn.config import Config
from uvicorn.server import Server


async def main():

    await asyncio.gather(
        Server(
            Config(
                app=settings.API_APP,
                host="0.0.0.0",
                port=settings.REPORT_SERVICE_PORT,
            )
        ).serve(),
    )


if __name__ == "__main__":
    asyncio.run(main())
