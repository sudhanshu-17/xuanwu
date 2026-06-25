"""Top-level API router, mounted under the ``/api/v2/xuanwu`` namespace."""

from fastapi import APIRouter

from app.api.v2.identity.router import identity_router

api_router = APIRouter(prefix="/api/v2/xuanwu")
api_router.include_router(identity_router, prefix="/identity", tags=["identity"])
