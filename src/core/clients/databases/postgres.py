from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
import os

from dotenv import load_dotenv

load_dotenv()


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


pg = PostgresClient()
