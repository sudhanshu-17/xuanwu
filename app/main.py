"""FastAPI application factory.

Phase 0: boots with a single ``/health`` route only. Routers, middleware,
exception handlers and settings are layered in from Phase 1 onward — see
``docs/engineering/PHASE-PLAN-AUTH-KICKSTART.md``.
"""

from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(
        title="Xuanwu Auth",
        version="0.1.0",
        description="Standalone authentication & authorization server.",
    )

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
