"""Integration tests for authentication + RBAC on protected routes."""

import time
import uuid

from app.core.security import hash_password
from app.models.api_key import APIKey
from app.models.user import User
from app.services.api_key_verifier import expected_signature
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

IDENTITY = "/api/v2/xuanwu/identity"
RESOURCE = "/api/v2/xuanwu/resource"
ADMIN = "/api/v2/xuanwu/admin"
PASSWORD = "Tr0ub4dour&3xtra"


def _email() -> str:
    return f"u{uuid.uuid4().hex[:12]}@example.com"


async def _login_as(client: AsyncClient, db: AsyncSession, role: str, state: str = "active") -> str:
    email = _email()
    db.add(
        User(
            email=email,
            password_digest=hash_password(PASSWORD),
            role=role,
            state=state,
        )
    )
    await db.commit()
    resp = await client.post(f"{IDENTITY}/sessions", json={"email": email, "password": PASSWORD})
    assert resp.status_code == 200, resp.text
    return str(resp.json()["data"]["csrf_token"])


async def test_protected_route_requires_authentication(client: AsyncClient) -> None:
    resp = await client.get(f"{RESOURCE}/users/me")
    assert resp.status_code == 401
    assert "authz.unauthorized" in resp.json()["errors"]


async def test_member_can_access_own_resource(client: AsyncClient, db: AsyncSession) -> None:
    await _login_as(client, db, role="member")
    resp = await client.get(f"{RESOURCE}/users/me")
    assert resp.status_code == 200
    assert resp.json()["data"]["role"] == "member"


async def test_member_forbidden_on_admin(client: AsyncClient, db: AsyncSession) -> None:
    await _login_as(client, db, role="member")
    resp = await client.get(f"{ADMIN}/ping")
    assert resp.status_code == 403
    assert "authz.forbidden" in resp.json()["errors"]


async def test_admin_allowed_on_admin(client: AsyncClient, db: AsyncSession) -> None:
    await _login_as(client, db, role="admin")
    resp = await client.get(f"{ADMIN}/ping")
    assert resp.status_code == 200
    assert resp.json()["data"]["pong"] is True


async def test_csrf_required_on_state_changing_request(
    client: AsyncClient, db: AsyncSession
) -> None:
    csrf = await _login_as(client, db, role="admin")
    missing = await client.post(f"{ADMIN}/ping")
    assert missing.status_code == 403
    assert "identity.csrf.invalid" in missing.json()["errors"]

    present = await client.post(f"{ADMIN}/ping", headers={"X-CSRF-Token": csrf})
    assert present.status_code == 200


async def test_banned_user_is_rejected(client: AsyncClient, db: AsyncSession) -> None:
    email = _email()
    db.add(
        User(email=email, password_digest=hash_password(PASSWORD), role="member", state="active")
    )
    await db.commit()
    login = await client.post(f"{IDENTITY}/sessions", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200
    # ban the user; the existing access cookie must stop working
    user = await db.scalar(select(User).where(User.email == email))
    assert user is not None
    user.state = "banned"
    await db.commit()
    resp = await client.get(f"{RESOURCE}/users/me")
    assert resp.status_code == 401


async def test_api_key_authorizes_via_hmac(client: AsyncClient, db: AsyncSession) -> None:
    email = _email()
    user = User(email=email, password_digest=hash_password(PASSWORD), role="member", state="active")
    db.add(user)
    await db.flush()
    kid, secret = "testkid" + uuid.uuid4().hex[:8], "super-secret-value-123"
    db.add(
        APIKey(
            kid=kid,
            secret=secret,
            key_holder_account_id=user.id,
            key_holder_account_type="User",
            state="active",
            scope=["read"],
        )
    )
    await db.commit()

    nonce = str(int(time.time() * 1000))
    signature = expected_signature(secret, nonce, kid)
    resp = await client.get(
        f"{RESOURCE}/users/me",
        headers={"X-Auth-Apikey": kid, "X-Auth-Nonce": nonce, "X-Auth-Signature": signature},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["email"] == email


async def test_api_key_bad_signature_rejected(client: AsyncClient, db: AsyncSession) -> None:
    email = _email()
    user = User(email=email, password_digest=hash_password(PASSWORD), role="member", state="active")
    db.add(user)
    await db.flush()
    kid = "testkid" + uuid.uuid4().hex[:8]
    db.add(
        APIKey(
            kid=kid,
            secret="the-real-secret",
            key_holder_account_id=user.id,
            key_holder_account_type="User",
            state="active",
        )
    )
    await db.commit()

    nonce = str(int(time.time() * 1000))
    resp = await client.get(
        f"{RESOURCE}/users/me",
        headers={"X-Auth-Apikey": kid, "X-Auth-Nonce": nonce, "X-Auth-Signature": "deadbeef"},
    )
    assert resp.status_code == 401
