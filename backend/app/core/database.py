from datetime import datetime, timezone
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


def utc_now() -> datetime:
    """Returns current UTC datetime without tzinfo for PostgreSQL / SQLite cross-engine compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


# Connect arguments for SQLite compatibility and PgBouncer/Neon compatibility
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
elif "asyncpg" in settings.DATABASE_URL:
    connect_args["statement_cache_size"] = 0
    connect_args["prepared_statement_cache_size"] = 0

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    connect_args=connect_args,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initializes tables for development/testing environments."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
