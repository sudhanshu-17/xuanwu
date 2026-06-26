"""Role-aware API documentation.

``/openapi.json`` is generated per request: a logged-in admin sees the full
schema (including ``/admin/*``), while everyone else gets those paths stripped.
Swagger UI and ReDoc are served from the same single URL for all visitors and
simply render whatever the schema exposes.

This is an information-disclosure reduction, not access control — the admin
endpoints stay protected by RBAC regardless of whether they appear in the docs.
The admin check is a soft read of the access-token cookie's ``role`` claim (no
database hit); a stale 15-minute token only affects what the docs *show*.
"""

from typing import Any

import jwt
from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, JSONResponse

from app.api.deps import ADMIN_ROLES
from app.core import security
from app.core.config import settings

# Admin routes live under the API namespace + ``/admin``.
ADMIN_PATH_PREFIX = "/api/v2/xuanwu/admin"


def _is_admin_request(request: Request) -> bool:
    token = request.cookies.get(settings.access_cookie_name)
    if not token:
        header = request.headers.get("authorization", "")
        if header.lower().startswith("bearer "):
            token = header[len("bearer ") :]
    if not token:
        return False
    try:
        payload = security.decode_token(token, expected_type=security.ACCESS_TYPE)
    except jwt.InvalidTokenError:
        return False
    return payload.get("role") in ADMIN_ROLES


def setup_docs(app: FastAPI) -> None:
    """Register the role-aware ``/openapi.json``, ``/docs`` and ``/redoc`` routes.

    Requires the app to be created with ``openapi_url=None, docs_url=None,
    redoc_url=None`` so these replace the defaults.
    """

    def full_schema() -> dict[str, Any]:
        if not app.openapi_schema:
            app.openapi_schema = get_openapi(
                title=app.title,
                version=app.version,
                description=app.description,
                routes=app.routes,
            )
        return app.openapi_schema

    def public_schema() -> dict[str, Any]:
        schema = full_schema()
        public = dict(schema)
        public["paths"] = {
            path: item
            for path, item in schema["paths"].items()
            if not path.startswith(ADMIN_PATH_PREFIX)
        }
        if "tags" in schema:
            public["tags"] = [tag for tag in schema["tags"] if tag.get("name") != "admin"]
        return public

    @app.get("/openapi.json", include_in_schema=False)
    async def openapi(request: Request) -> JSONResponse:
        return JSONResponse(full_schema() if _is_admin_request(request) else public_schema())

    @app.get("/docs", include_in_schema=False)
    async def swagger_ui() -> HTMLResponse:
        return get_swagger_ui_html(openapi_url="/openapi.json", title=f"{app.title} — Swagger UI")

    @app.get("/redoc", include_in_schema=False)
    async def redoc() -> HTMLResponse:
        return get_redoc_html(openapi_url="/openapi.json", title=f"{app.title} — ReDoc")
