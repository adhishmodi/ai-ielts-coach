from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import settings


# Vercel runs the FastAPI app in short-lived serverless instances. Keeping a
# SQLAlchemy connection pool inside each instance can exhaust connections and
# make asyncpg/DNS connection attempts unreliable. NullPool lets Supabase/
# Supavisor own the connection pooling instead.
engine_kwargs = {
    "echo": False,
    "poolclass": NullPool,
    "connect_args": {
        "timeout": 10,
    },
}


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
