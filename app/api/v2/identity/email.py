"""Email verification."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.schemas.common import Envelope
from app.schemas.identity import EmailCodeOut, EmailConfirmIn, EmailGenerateIn, UserOut
from app.services import auth_service

router = APIRouter()


@router.post("/email/generate_code", response_model=Envelope[EmailCodeOut])
async def generate_email_code(
    payload: EmailGenerateIn, db: AsyncSession = Depends(get_db)
) -> Envelope[EmailCodeOut]:
    user = await auth_service.get_user_by_email(db, payload.email)
    token = auth_service.make_email_token(user) if user else None
    # Delivery is handled by the email worker (Phase 9); outside production we
    # return the token so the flow is testable without a mail server.
    return Envelope[EmailCodeOut](
        data=EmailCodeOut(
            message="If the account exists, a confirmation link has been sent.",
            confirmation_token=None if settings.is_production else token,
        )
    )


@router.post("/email/confirm_code", response_model=Envelope[UserOut])
async def confirm_email_code(
    payload: EmailConfirmIn, db: AsyncSession = Depends(get_db)
) -> Envelope[UserOut]:
    user = await auth_service.confirm_email(db, token=payload.token)
    return Envelope[UserOut](data=UserOut.model_validate(user))
