"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.redis import check_redis
from app.db.session import check_database

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    logger.info(
        "startup",
        app_env=settings.app_env,
        database=await check_database(),
        redis=await check_redis(),
    )
    yield


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title="Xuanwu Auth",
        version="0.1.0",
        description="Standalone authentication & authorization server.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready", tags=["health"])
    async def readiness() -> dict[str, object]:
        database_ok = await check_database()
        redis_ok = await check_redis()
        return {
            "status": "ok" if database_ok and redis_ok else "degraded",
            "database": database_ok,
            "redis": redis_ok,
        }

    return app


app = create_app()
