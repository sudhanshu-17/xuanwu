"""Phone management. SMS delivery is wired in Phase 10; the code is generated
and stored here so verification works end to end in the meantime."""

import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import APIError
from app.models.label import Label
from app.models.phone import Phone
from app.models.user import User
from app.utils.blind_index import blind_index


def _generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


async def list_phones(db: AsyncSession, user_id: uuid.UUID) -> list[Phone]:
    rows = await db.scalars(select(Phone).where(Phone.user_id == user_id))
    return list(rows.all())


async def create_phone(
    db: AsyncSession, user: User, *, country: str | None, number: str
) -> tuple[Phone, str]:
    code = _generate_code()
    phone = Phone(
        user_id=user.id,
        country=country,
        number=number,
        number_index=blind_index(number),
        code=code,
    )
    db.add(phone)
    await db.commit()
    await db.refresh(phone)
    return phone, code


async def verify_phone(db: AsyncSession, user: User, *, phone_id: uuid.UUID, code: str) -> Phone:
    phone = await db.scalar(select(Phone).where(Phone.id == phone_id, Phone.user_id == user.id))
    if phone is None:
        raise APIError(["resource.phone.not_found"], 404)
    if phone.validated_at is not None:
        return phone
    if not phone.code or not secrets.compare_digest(phone.code, code):
        raise APIError(["resource.phone.invalid_code"], 422)

    phone.validated_at = datetime.now(UTC)
    phone.code = None
    existing = await db.scalar(
        select(Label).where(
            Label.user_id == user.id, Label.key == "phone", Label.scope == "private"
        )
    )
    if existing is None:
        db.add(Label(user_id=user.id, key="phone", value="verified", scope="private"))
    await db.commit()
    await db.refresh(phone)
    return phone
