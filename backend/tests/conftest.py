import asyncio
import os
from pathlib import Path
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DB_PATH = Path("./test_platform.db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["STORAGE_PROVIDER_TYPE"] = "LOCAL"
os.environ["LOCAL_STORAGE_BASE_PATH"] = "./storage_test"

import app.core.database as app_db
from app.core.database import Base
from app.main import app


# Create unified test engine
test_engine = create_async_engine(f"sqlite+aiosqlite:///{TEST_DB_PATH.as_posix()}", echo=False)
test_session_maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

# Override the app's global sessionmaker and engine so background tasks and dependencies share it
app_db.engine = test_engine
app_db.async_session_maker = test_session_maker


@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def prepare_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass


async def override_get_db():
    async with test_session_maker() as session:
        yield session


app.dependency_overrides[app_db.get_db] = override_get_db


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
