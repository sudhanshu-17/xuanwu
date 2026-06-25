"""Shared pytest fixtures."""

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
import redis.asyncio as redis
from app.api.deps import get_redis
from app.core.config import settings
from app.db.session import get_db
from app.main import app
from fakeredis import FakeAsyncRedis
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


@pytest.fixture
def fake_redis() -> redis.Redis:
    """An in-memory async Redis, so Redis-backed logic is unit-testable offline."""
    return FakeAsyncRedis(decode_responses=True)


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """HTTP client wired to the app, with a per-test DB engine and Redis.

    Each test gets its own connections (created and disposed on its own event
    loop) via dependency overrides, avoiding cross-loop sharing of the app's
    global pools. Skips when no database is reachable.
    """
    test_engine = create_async_engine(settings.database_url, poolclass=NullPool)
    try:
        async with test_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        await test_engine.dispose()
        pytest.skip("requires a running database")

    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    test_redis: redis.Redis = redis.from_url(  # type: ignore[no-untyped-call]
        settings.redis_url, decode_responses=True
    )

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    async def _override_get_redis() -> redis.Redis:
        return test_redis

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_redis] = _override_get_redis
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
            yield http_client
    finally:
        app.dependency_overrides.clear()
        await test_redis.aclose()
        await test_engine.dispose()
