"""Role-aware API docs: /admin/* is visible in the schema only to admins."""

import uuid
from typing import Any

from app.core.security import hash_password
from app.models.user import User
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

IDENTITY = "/api/v2/xuanwu/identity"
ADMIN_PREFIX = "/api/v2/xuanwu/admin"
PASSWORD = "Tr0ub4dour&3xtra"


def _email() -> str:
    return f"u{uuid.uuid4().hex[:12]}@example.com"


async def _login_as(client: AsyncClient, db: AsyncSession, role: str) -> None:
    email = _email()
    db.add(User(email=email, password_digest=hash_password(PASSWORD), role=role, state="active"))
    await db.commit()
    resp = await client.post(f"{IDENTITY}/sessions", json={"email": email, "password": PASSWORD})
    assert resp.status_code == 200, resp.text


def _has_admin_paths(schema: dict[str, Any]) -> bool:
    return any(path.startswith(ADMIN_PREFIX) for path in schema["paths"])


async def test_anonymous_schema_hides_admin(client: AsyncClient) -> None:
    schema = (await client.get("/openapi.json")).json()
    assert not _has_admin_paths(schema)
    # Public surface is still present.
    assert any(p.startswith("/api/v2/xuanwu/identity") for p in schema["paths"])


async def test_member_schema_hides_admin(client: AsyncClient, db: AsyncSession) -> None:
    await _login_as(client, db, role="member")
    schema = (await client.get("/openapi.json")).json()
    assert not _has_admin_paths(schema)


async def test_admin_schema_includes_admin(client: AsyncClient, db: AsyncSession) -> None:
    await _login_as(client, db, role="admin")
    schema = (await client.get("/openapi.json")).json()
    assert _has_admin_paths(schema)


async def test_docs_page_renders(client: AsyncClient) -> None:
    resp = await client.get("/docs")
    assert resp.status_code == 200
    assert "swagger-ui" in resp.text.lower()
