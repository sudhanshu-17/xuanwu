"""Celery task that renders and delivers a branded transactional email.

Rendering happens inside the task (not the caller) so a retry re-renders from
the original arguments. Delivery uses the configured provider; transient
failures are retried up to three times, five minutes apart.
"""

from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.emails import render_email
from app.integrations.email import EmailMessage, get_provider
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(  # type: ignore[untyped-decorator]
    name="email.send", bind=True, max_retries=3, default_retry_delay=300
)
def send_email(
    self: Any,
    *,
    to: str,
    template: str,
    context: dict[str, Any],
    lang: str | None = None,
) -> None:
    rendered = render_email(template, lang or settings.email_default_language, context)
    message = EmailMessage(
        to=to,
        subject=rendered.subject,
        html=rendered.html,
        text=rendered.text,
        from_email=settings.email_from,
        from_name=settings.email_from_name,
    )
    try:
        get_provider().send(message)
    except Exception as exc:
        logger.warning("email_send_failed", to=to, template=template, exc_info=True)
        raise self.retry(exc=exc) from exc
    logger.info("email_enqueued_sent", to=to, template=template)
