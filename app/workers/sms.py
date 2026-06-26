"""Celery task that delivers a single SMS through the configured provider.

Transient failures are retried up to three times, five minutes apart.
"""

from typing import Any

from app.core.logging import get_logger
from app.integrations.sms import SMSMessage, get_provider
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(  # type: ignore[untyped-decorator]
    name="sms.send", bind=True, max_retries=3, default_retry_delay=300
)
def send_sms(self: Any, *, to: str, body: str) -> None:
    try:
        get_provider().send(SMSMessage(to=to, body=body))
    except Exception as exc:
        logger.warning("sms_send_failed", to=to, exc_info=True)
        raise self.retry(exc=exc) from exc
    logger.info("sms_sent", to=to)
