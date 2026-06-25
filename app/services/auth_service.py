"""Authentication business logic: registration, login, email/password flows.

Routers validate and serialize; all the rules live here. Failures raise
``APIError`` with dotted i18n keys.
"""

import datetime as dt
import uuid
from typing import cast

import jwt
import redis.asyncio as redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import settings
from app.core.errors import APIError
from app.core.tokens import TokenPair, TokenService
from app.models.enums import UserState
from app.models.label import Label
from app.models.user import User
from app.services.password_strength import password_errors
from app.services.totp import TOTPService

EMAIL_CONFIRM_TYPE = "email_confirm"
PASSWORD_RESET_TYPE = "password_reset"  # token type, not a secret  # nosec B105
_EMAIL_TOKEN_TTL = 3600  # 1 hour
_PASSWORD_TOKEN_TTL = 1800  # 30 minutes


# --- lookups -----------------------------------------------------------------
async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    return cast("User | None", await db.scalar(select(User).where(User.email == email)))


# --- registration ------------------------------------------------------------
async def register(db: AsyncSession, *, email: str, password: str, username: str | None) -> User:
    errors = password_errors(password)
    if errors:
        raise APIError(errors, 422)

    if await get_user_by_email(db, email) is not None:
        raise APIError(["identity.user.email_taken"], 409)
    if username and await db.scalar(select(User).where(User.username == username)) is not None:
        raise APIError(["identity.user.username_taken"], 409)

    is_first = settings.first_user_superadmin and (
        await db.scalar(select(func.count()).select_from(User)) == 0
    )
    user = User(
        email=email,
        username=username,
        password_digest=security.hash_password(password),
        role="superadmin" if is_first else "member",
        state=UserState.active.value if is_first else UserState.pending.value,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def make_email_token(user: User) -> str:
    token, _ = security.create_token(
        user_id=str(user.id),
        token_type=EMAIL_CONFIRM_TYPE,
        ttl=_EMAIL_TOKEN_TTL,
        extra={"email": user.email},
    )
    return token


# --- login + lockout ---------------------------------------------------------
def _lockout_key(email: str, ip: str) -> str:
    return f"login_attempts:{email}:{ip}"


async def _record_failure(redis_client: redis.Redis, key: str) -> None:
    attempts = await redis_client.incr(key)
    if attempts == 1:
        await redis_client.expire(key, settings.login_lockout_ttl)


async def login(
    db: AsyncSession,
    redis_client: redis.Redis,
    *,
    email: str,
    password: str,
    otp_code: str | None,
    ip: str,
) -> tuple[User, TokenPair]:
    key = _lockout_key(email, ip)
    attempts = await redis_client.get(key)
    if attempts is not None and int(attempts) >= settings.login_max_attempts:
        raise APIError(["identity.session.locked"], 429)

    user = await get_user_by_email(db, email)
    if user is None or not security.verify_password(password, user.password_digest):
        await _record_failure(redis_client, key)
        raise APIError(["identity.session.invalid_credentials"], 401)
    if user.state == UserState.banned.value:
        raise APIError(["identity.session.banned"], 401)
    if user.state == UserState.deleted.value:
        raise APIError(["identity.session.invalid_credentials"], 401)

    if user.otp:
        secret = user.otp_secret
        if not otp_code:
            raise APIError(["identity.session.missing_otp"], 401)
        if secret is None or not await TOTPService(redis_client).verify(
            str(user.id), secret, otp_code
        ):
            await _record_failure(redis_client, key)
            raise APIError(["identity.session.invalid_otp"], 401)

    await redis_client.delete(key)
    pair = await TokenService(redis_client).issue_pair(user_id=str(user.id), role=user.role)
    return user, pair


# --- email confirmation ------------------------------------------------------
async def confirm_email(db: AsyncSession, *, token: str) -> User:
    try:
        payload = security.decode_token(token, expected_type=EMAIL_CONFIRM_TYPE)
    except jwt.InvalidTokenError as exc:
        raise APIError(["identity.email.invalid_token"], 422) from exc

    user = await db.get(User, uuid.UUID(payload["uid"]))
    if user is None:
        raise APIError(["identity.email.invalid_token"], 422)

    existing = await db.scalar(
        select(Label).where(
            Label.user_id == user.id, Label.key == "email", Label.scope == "private"
        )
    )
    if existing is None:
        db.add(Label(user_id=user.id, key="email", value="verified", scope="private"))
    if user.state == UserState.pending.value:
        user.state = UserState.active.value
    await db.commit()
    await db.refresh(user)
    return user


# --- password reset ----------------------------------------------------------
async def request_password_reset(db: AsyncSession, *, email: str) -> str | None:
    user = await get_user_by_email(db, email)
    if user is None:
        return None
    token, _ = security.create_token(
        user_id=str(user.id), token_type=PASSWORD_RESET_TYPE, ttl=_PASSWORD_TOKEN_TTL
    )
    return token


async def reset_password(
    db: AsyncSession, redis_client: redis.Redis, *, token: str, password: str
) -> User:
    errors = password_errors(password)
    if errors:
        raise APIError(errors, 422)
    try:
        payload = security.decode_token(token, expected_type=PASSWORD_RESET_TYPE)
    except jwt.InvalidTokenError as exc:
        raise APIError(["identity.password.invalid_token"], 422) from exc

    user = await db.get(User, uuid.UUID(payload["uid"]))
    if user is None:
        raise APIError(["identity.password.invalid_token"], 422)

    user.password_digest = security.hash_password(password)
    await db.commit()
    await TokenService(redis_client).invalidate_all(str(user.id))  # log out everywhere
    await db.refresh(user)
    return user


def validate_reset_token(token: str) -> bool:
    try:
        security.decode_token(token, expected_type=PASSWORD_RESET_TYPE)
    except jwt.InvalidTokenError:
        return False
    return True


def now_iso() -> str:
    return dt.datetime.now(dt.UTC).isoformat()
