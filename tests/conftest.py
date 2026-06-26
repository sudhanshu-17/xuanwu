"""Shared pytest fixtures."""

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
import redis.asyncio as redis
from app.api.deps import get_redis
from app.core.config import settings
from app.db.seeds import seed_levels, seed_permissions
from app.db.session import get_db
from app.main import app
from fakeredis import FakeAsyncRedis
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

_SEEDED_ROLES = ("superadmin", "admin", "member", "guest")


@pytest.fixture(autouse=True)
def _eager_celery() -> None:
    """Run Celery tasks inline (no broker/worker) so audit/email work happens in-test."""
    from app.workers.celery_app import celery_app

    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True


@pytest.fixture(autouse=True)
def _mock_email() -> None:
    """Capture outgoing email in memory and reset the outbox between tests."""
    from app.core.config import settings
    from app.integrations.email import mock

    settings.email_provider = "mock"
    mock.clear()


@pytest.fixture(autouse=True)
def _mock_sms() -> None:
    """Capture outgoing SMS in memory and reset the outbox between tests."""
    from app.core.config import settings
    from app.integrations.sms import mock

    settings.sms_provider = "mock"
    mock.clear()


@pytest.fixture(autouse=True)
def _local_storage(tmp_path: object) -> None:
    """Store uploads under a throwaway temp directory, not the repo tree."""
    from app.core.config import settings

    settings.storage_provider = "local"
    settings.upload_dir = str(tmp_path)


@pytest.fixture
def fake_redis() -> redis.Redis:
    """An in-memory async Redis, so Redis-backed logic is unit-testable offline."""
    return FakeAsyncRedis(decode_responses=True)


@pytest_asyncio.fixture
async def _engine() -> AsyncIterator[AsyncEngine]:
    """A per-test engine (own event loop). Skips when no database is reachable."""
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        await engine.dispose()
        pytest.skip("requires a running database")
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db(_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """A session for arranging test data, sharing the client's engine."""
    async with async_sessionmaker(_engine, expire_on_commit=False)() as session:
        yield session


@pytest_asyncio.fixture
async def client(_engine: AsyncEngine) -> AsyncIterator[AsyncClient]:
    """HTTP client wired to the app with per-test DB + Redis and seeded RBAC."""
    session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    test_redis: redis.Redis = redis.from_url(  # type: ignore[no-untyped-call]
        settings.redis_url, decode_responses=True
    )
    async with session_factory() as setup_session:
        await seed_permissions(setup_session)
        await seed_levels(setup_session)
    for role in _SEEDED_ROLES:
        await test_redis.delete(f"permissions:{role}")

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
