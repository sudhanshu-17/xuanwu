"""Public metadata: ping, server time, and client-safe configuration."""

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.common import Envelope
from app.schemas.identity import ConfigsOut, PasswordPolicyOut
from app.services import auth_service

router = APIRouter()


@router.get("/ping", response_model=Envelope[dict[str, str]])
async def ping() -> Envelope[dict[str, str]]:
    return Envelope[dict[str, str]](data={"ping": "pong"})


@router.get("/time", response_model=Envelope[dict[str, str]])
async def server_time() -> Envelope[dict[str, str]]:
    return Envelope[dict[str, str]](data={"time": auth_service.now_iso()})


@router.get("/configs", response_model=Envelope[ConfigsOut])
async def configs() -> Envelope[ConfigsOut]:
    return Envelope[ConfigsOut](
        data=ConfigsOut(
            password=PasswordPolicyOut(
                min_length=settings.password_min_length,
                max_length=settings.password_max_length,
                min_score=settings.password_min_score,
            ),
            captcha_provider=settings.captcha_provider,
            recaptcha_site_key=settings.recaptcha_site_key or None,
        )
    )
