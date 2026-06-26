"""Typed helpers that enqueue branded emails.

Services and routers call these instead of touching the Celery task directly, so
link construction and context shape live in one place.
"""

from app.core.config import settings
from app.models.user import User
from app.workers.email import send_email


def send_confirmation_email(user: User, token: str) -> None:
    url = f"{settings.frontend_url}/confirm-email?token={token}"
    send_email.delay(to=user.email, template="confirmation", context={"confirmation_url": url})


def send_password_reset_email(user: User, token: str) -> None:
    url = f"{settings.frontend_url}/reset-password?token={token}"
    send_email.delay(to=user.email, template="password_reset", context={"reset_url": url})


def send_session_create_email(user: User, *, ip: str | None, user_agent: str | None) -> None:
    send_email.delay(
        to=user.email,
        template="session_create",
        context={"ip": ip, "user_agent": user_agent},
    )


def send_label_email(user: User, *, key: str, value: str) -> None:
    send_email.delay(
        to=user.email,
        template="label",
        context={"label_key": key, "label_value": value},
    )
