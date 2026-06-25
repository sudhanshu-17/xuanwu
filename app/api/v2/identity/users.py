"""User registration."""

import redis.asyncio as redis
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_redis
from app.core import tokens as token_cookies
from app.core.tokens import TokenService
from app.db.session import get_db
from app.schemas.common import Envelope
from app.schemas.identity import RegisterIn, SessionOut, UserOut
from app.services import auth_service

router = APIRouter()


@router.post("/users", response_model=Envelope[SessionOut], status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: RegisterIn,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> Envelope[SessionOut]:
    user = await auth_service.register(
        db, email=payload.email, password=payload.password, username=payload.username
    )
    # Email confirmation is sent via /email/generate_code (delivery worker: Phase 9).
    pair = await TokenService(redis_client).issue_pair(user_id=str(user.id), role=user.role)
    token_cookies.set_auth_cookies(response, pair)
    return Envelope[SessionOut](
        data=SessionOut(user=UserOut.model_validate(user), csrf_token=pair.csrf_token)
    )
