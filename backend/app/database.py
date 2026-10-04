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


database_url = settings.database_url.strip()

# Vercel/Supabase commonly provide PostgreSQL URLs without an explicit
# SQLAlchemy driver. This application uses asyncpg everywhere, so normalize
# those URLs before creating the async engine.
if database_url.startswith("postgres://"):
    database_url = "postgresql+asyncpg://" + database_url[len("postgres://"):]
elif database_url.startswith("postgresql://"):
    database_url = "postgresql+asyncpg://" + database_url[len("postgresql://"):]


engine = create_async_engine(
    database_url,
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
