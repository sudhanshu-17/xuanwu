"""Top-level API router, mounted under the ``/api/v2/xuanwu`` namespace."""

from fastapi import APIRouter

from app.api.v2.admin.router import admin_router
from app.api.v2.identity.router import identity_router
from app.api.v2.resource.router import resource_router

api_router = APIRouter(prefix="/api/v2/xuanwu")
api_router.include_router(identity_router, prefix="/identity", tags=["identity"])
api_router.include_router(resource_router, prefix="/resource", tags=["resource"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
