"""In-memory SMS provider for development and tests.

Captured messages are appended to :data:`outbox`; tests assert against it and
call :func:`clear` between cases.
"""

from app.core.logging import get_logger
from app.integrations.sms.base import SMSMessage

logger = get_logger(__name__)

outbox: list[SMSMessage] = []


def clear() -> None:
    outbox.clear()


class MockSMSProvider:
    def send(self, message: SMSMessage) -> None:
        outbox.append(message)
        logger.info("sms_sent_mock", to=message.to)
