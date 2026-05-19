from api.settings import settings
from database.models import Base
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

aengine_master = create_async_engine(
    settings.DB_MASTER_URL,
    echo=False,
)

aengine_slave = create_async_engine(
    settings.DB_SLAVE_URL,
    echo=False,
)


SessionLocalMaster = async_sessionmaker(
    bind=aengine_master,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)

SessionLocalSlave = async_sessionmaker(
    bind=aengine_slave,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)


async def get_write_session():
    session = SessionLocalMaster()
    try:
        yield session
    finally:
        await session.close()


async def get_read_session():
    session = SessionLocalSlave()
    try:
        yield session
    finally:
        await session.close()


async def _set_up_master_slave():
    async with aengine_master.connect() as conn:
        conn = await conn.execution_options(isolation_level="AUTOCOMMIT")
        await conn.execute(text(f"""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_roles WHERE rolname = '{settings.REPL_USER}'
                    ) THEN
                        CREATE ROLE {settings.REPL_USER}
                            WITH LOGIN REPLICATION PASSWORD '{settings.REPL_PASSWORD}';
                    END IF;
                END
                $$;
                """))

    async with aengine_master.connect() as conn:
        conn = await conn.execution_options(isolation_level="AUTOCOMMIT")

        slot_exists = await conn.scalar(text("""
                SELECT EXISTS (
                    SELECT 1
                    FROM pg_replication_slots
                    WHERE slot_name = 'app_sub'
                );
                """))

        if slot_exists:
            await conn.execute(text("""
                    SELECT pg_drop_replication_slot('app_sub');
                    """))

    async with aengine_master.connect() as conn:
        conn = await conn.execution_options(isolation_level="AUTOCOMMIT")
        await conn.execute(text("DROP PUBLICATION IF EXISTS app_pub;"))
        await conn.execute(text("""
                CREATE PUBLICATION app_pub
                FOR TABLE users, products, orders, order_items, auth, service_tokens
                WITH (publish = 'insert, update, delete');
                """))

    async with aengine_slave.connect() as conn:
        conn = await conn.execution_options(isolation_level="AUTOCOMMIT")
        await conn.execute(text("DROP SUBSCRIPTION IF EXISTS app_sub;"))
        await conn.execute(text(f"""
                CREATE SUBSCRIPTION app_sub
                CONNECTION '{settings.CONNECTION_FROM_SLAVE_TO_MASTER_URL}'
                PUBLICATION app_pub
                WITH (copy_data = false);
                """))


async def _init_dbs():
    async with aengine_master.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with aengine_slave.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    await _set_up_master_slave()


async def _soft_init_dbs():
    async with aengine_master.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with aengine_slave.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await _set_up_master_slave()
