"""Password reset."""

import redis.asyncio as redis
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_redis
from app.core.config import settings
from app.db.session import get_db
from app.schemas.common import Envelope, Message
from app.schemas.identity import PasswordCodeOut, PasswordConfirmIn, PasswordGenerateIn, ValidityOut
from app.services import auth_service

router = APIRouter()


@router.post("/password/generate_code", response_model=Envelope[PasswordCodeOut])
async def generate_password_code(
    payload: PasswordGenerateIn, db: AsyncSession = Depends(get_db)
) -> Envelope[PasswordCodeOut]:
    token = await auth_service.request_password_reset(db, email=payload.email)
    return Envelope[PasswordCodeOut](
        data=PasswordCodeOut(
            message="If the account exists, a reset link has been sent.",
            reset_token=None if settings.is_production else token,
        )
    )


@router.post("/password/confirm_code", response_model=Envelope[Message])
async def confirm_password_code(
    payload: PasswordConfirmIn,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> Envelope[Message]:
    await auth_service.reset_password(
        db, redis_client, token=payload.token, password=payload.password
    )
    return Envelope[Message](data=Message(message="Password updated."))


@router.get("/password/validate", response_model=Envelope[ValidityOut])
async def validate_password_token(token: str) -> Envelope[ValidityOut]:
    return Envelope[ValidityOut](data=ValidityOut(valid=auth_service.validate_reset_token(token)))
