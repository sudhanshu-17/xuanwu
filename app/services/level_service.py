"""Progressive-verification engine: labels → level + state.

Labels are the raw events ("email=verified", "banned=true"). This module is the
single place that translates the set of *private* labels a user holds into their
numeric ``level`` (driven by the ``levels`` table) and account ``state`` (driven
by ``config/auth.yml`` ``state_triggers``).

It is invoked explicitly by the services that add or remove labels — there are
no hidden ORM callbacks (ARCHITECTURE §3.1). A label change always flows through
:func:`add_label` / :func:`remove_label`, which re-derive level and state and,
when an account becomes banned or deleted, revoke every active session.
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import redis.asyncio as redis
import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.tokens import TokenService
from app.models.enums import LabelScope, UserState
from app.models.label import Label
from app.models.level import Level
from app.models.user import User

# System labels live in the private scope; public labels never affect level/state.
SYSTEM_SCOPE = LabelScope.private.value
_LOCKING_STATES = frozenset({UserState.banned.value, UserState.deleted.value})


@dataclass(frozen=True)
class StateTrigger:
    key: str
    value: str
    state: str


@lru_cache
def load_state_triggers() -> tuple[StateTrigger, ...]:
    """State triggers from ``config/auth.yml``, in evaluation order."""
    path = Path(settings.auth_config_path)
    if not path.exists():
        return ()
    data = yaml.safe_load(path.read_text()) or {}
    triggers = []
    for raw in data.get("state_triggers") or []:
        triggers.append(
            StateTrigger(
                key=str(raw["key"]),
                value=str(raw["value"]),
                state=str(raw["state"]),
            )
        )
    return tuple(triggers)


async def _held_labels(db: AsyncSession, user_id: object) -> set[tuple[str, str]]:
    """The (key, value) pairs of every private label the user currently holds."""
    rows = await db.scalars(
        select(Label).where(Label.user_id == user_id, Label.scope == SYSTEM_SCOPE)
    )
    return {(row.key, row.value) for row in rows.all()}


async def recompute_level(db: AsyncSession, user: User) -> None:
    """Set ``user.level`` to the highest contiguous verified level.

    Levels are ordered by id; the first missing label stops progression, so a
    user with email+document but no phone stays at level 1, not 3.
    """
    held = await _held_labels(db, user.id)
    levels = (await db.scalars(select(Level).order_by(Level.id))).all()
    new_level = 0
    for level in levels:
        if (level.key, level.value) in held:
            new_level = level.id
        else:
            break
    user.level = new_level


async def recompute_state(db: AsyncSession, user: User) -> bool:
    """Re-derive ``user.state`` from state triggers.

    Returns ``True`` when the resulting state locks the account (banned/deleted),
    signalling the caller to revoke the user's sessions.
    """
    held = await _held_labels(db, user.id)
    for trigger in load_state_triggers():
        if (trigger.key, trigger.value) in held:
            user.state = trigger.state
            return trigger.state in _LOCKING_STATES

    # No locking trigger is active: lift a ban, and activate a pending account
    # once its email is verified. `deleted` is terminal and never auto-restored.
    lift_ban = user.state == UserState.banned.value
    activate = user.state == UserState.pending.value and ("email", "verified") in held
    if lift_ban or activate:
        user.state = UserState.active.value
    return False


async def _sync(db: AsyncSession, user: User, redis_client: redis.Redis | None) -> None:
    """Flush the pending label change, re-derive level + state, persist, revoke."""
    await db.flush()  # make the label add/remove visible to the recompute queries
    await recompute_level(db, user)
    locked = await recompute_state(db, user)
    await db.commit()
    await db.refresh(user)
    if locked and redis_client is not None:
        await TokenService(redis_client).invalidate_all(str(user.id))


async def add_label(
    db: AsyncSession,
    user: User,
    *,
    key: str,
    value: str = "verified",
    redis_client: redis.Redis | None = None,
) -> Label:
    """Add or update a private system label, then re-derive level and state.

    Idempotent on ``(user, key)``: an existing label's value is updated in place.
    """
    label = await db.scalar(
        select(Label).where(Label.user_id == user.id, Label.key == key, Label.scope == SYSTEM_SCOPE)
    )
    if label is None:
        label = Label(user_id=user.id, key=key, value=value, scope=SYSTEM_SCOPE)
        db.add(label)
    else:
        label.value = value
    await _sync(db, user, redis_client)
    return label


async def remove_label(
    db: AsyncSession,
    user: User,
    *,
    key: str,
    redis_client: redis.Redis | None = None,
) -> None:
    """Remove a private system label (if present), then re-derive level and state."""
    label = await db.scalar(
        select(Label).where(Label.user_id == user.id, Label.key == key, Label.scope == SYSTEM_SCOPE)
    )
    if label is not None:
        await db.delete(label)
    await _sync(db, user, redis_client)
