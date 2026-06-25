"""Shared pytest fixtures."""

import pytest
import redis.asyncio as redis
from fakeredis import FakeAsyncRedis


@pytest.fixture
def fake_redis() -> redis.Redis:
    """An in-memory async Redis, so Redis-backed logic is unit-testable offline."""
    return FakeAsyncRedis(decode_responses=True)
