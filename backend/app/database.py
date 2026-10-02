import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import settings


is_testing = os.getenv("ENV_FILE") == ".env.test" or os.getenv("TESTING") == "1"

engine_kwargs = {
    "echo": True,
}

if is_testing:
    engine_kwargs["poolclass"] = NullPool


engine = create_async_engine(
    settings.database_url,
    **engine_kwargs,
)


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session