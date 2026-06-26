"""Progressive-verification engine: labels drive level and state."""

import uuid

import redis.asyncio as redis
from app.core.tokens import TokenService
from app.models.enums import UserState
from app.models.user import User
from app.services import level_service
from sqlalchemy.ext.asyncio import AsyncSession


def test_state_triggers_loaded_from_config() -> None:
    """The config ships the ban/delete triggers (no database needed)."""
    triggers = {(t.key, t.value): t.state for t in level_service.load_state_triggers()}
    assert triggers[("banned", "true")] == UserState.banned.value
    assert triggers[("deleted", "true")] == UserState.deleted.value


async def _make_user(db: AsyncSession) -> User:
    user = User(email=f"u{uuid.uuid4().hex[:12]}@example.com", password_digest="x")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def test_email_label_bumps_level_and_activates(db: AsyncSession) -> None:
    user = await _make_user(db)
    assert user.level == 0
    assert user.state == UserState.pending.value

    await level_service.add_label(db, user, key="email", value="verified")

    assert user.level == 1
    assert user.state == UserState.active.value


async def test_level_progression_stops_at_first_gap(db: AsyncSession) -> None:
    user = await _make_user(db)
    await level_service.add_label(db, user, key="email", value="verified")
    # Document verified but phone missing → a gap; level stays at email (1).
    await level_service.add_label(db, user, key="document", value="verified")
    assert user.level == 1
    # Filling the phone gap unlocks the contiguous run up to document (3).
    await level_service.add_label(db, user, key="phone", value="verified")
    assert user.level == 3


async def test_remove_label_drops_level(db: AsyncSession) -> None:
    user = await _make_user(db)
    await level_service.add_label(db, user, key="email", value="verified")
    assert user.level == 1

    await level_service.remove_label(db, user, key="email")
    assert user.level == 0


async def test_ban_label_flips_state_and_revokes_sessions(
    db: AsyncSession, fake_redis: redis.Redis
) -> None:
    user = await _make_user(db)
    tokens = TokenService(fake_redis)
    await tokens.issue_pair(user_id=str(user.id), role=user.role)
    assert await fake_redis.smembers(f"user:{user.id}:refresh")  # type: ignore[misc]

    await level_service.add_label(db, user, key="banned", value="true", redis_client=fake_redis)

    assert user.state == UserState.banned.value
    assert not await fake_redis.smembers(f"user:{user.id}:refresh")  # type: ignore[misc]


async def test_unban_restores_active(db: AsyncSession) -> None:
    user = await _make_user(db)
    await level_service.add_label(db, user, key="banned", value="true")
    assert user.state == UserState.banned.value

    await level_service.remove_label(db, user, key="banned")
    assert user.state == UserState.active.value
