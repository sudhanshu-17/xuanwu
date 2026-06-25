"""Shared FastAPI dependencies."""

import redis.asyncio as redis
from fastapi import Request

from app.core.redis import redis_client


async def get_redis() -> redis.Redis:
    return redis_client


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"
