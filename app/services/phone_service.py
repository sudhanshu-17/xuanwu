"""Phone management: store a number (encrypted + blind-indexed), send a
verification code by SMS, and on success record the ``phone=verified`` label
through the progressive-verification engine."""

import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import APIError
from app.models.phone import Phone
from app.models.user import User
from app.services import level_service
from app.utils.blind_index import blind_index
from app.workers.sms import send_sms


def _generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _verification_body(code: str) -> str:
    return f"Your Rare Vintage verification code is {code}."


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
    send_sms.delay(to=number, body=_verification_body(code))
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
    # The level engine commits the pending phone changes, adds the private
    # phone=verified label, and re-derives the user's level (and state).
    await level_service.add_label(db, user, key="phone", value="verified")
    await db.refresh(phone)
    return phone
