from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
import os
from sqlalchemy import text


class PostgresClient:
    dsn = (
        f"postgresql+asyncpg://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
        f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
    )

    def __init__(self):
        self.engine = create_async_engine(self.dsn, echo=False)
        self.session_maker = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def test_connection(self):
        async with self.session_maker() as session:
            result = await session.execute(text("SELECT 1"))
            value = result.scalar_one()
            print(f"✅ Проверка подключения: {value}")
            return value


pg = PostgresClient()