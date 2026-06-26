"""SMS provider selection.

``get_provider()`` returns the provider named by ``SMS_PROVIDER``. The default
``mock`` keeps development and tests offline; ``twilio_sms`` and ``aws_sns`` are
the real backends.

(Twilio Verify — where Twilio both issues and checks the code — is intentionally
not here: it replaces our own code generation/verification rather than acting as
a message sender, so it would need a different service flow.)
"""

from app.core.config import settings
from app.integrations.sms.aws_sns import AWSSNSProvider
from app.integrations.sms.base import SMSMessage, SMSProvider
from app.integrations.sms.mock import MockSMSProvider
from app.integrations.sms.twilio_sms import TwilioSMSProvider

__all__ = ["SMSMessage", "SMSProvider", "get_provider"]


def get_provider() -> SMSProvider:
    provider = settings.sms_provider.lower()
    if provider == "twilio_sms":
        return TwilioSMSProvider()
    if provider == "aws_sns":
        return AWSSNSProvider()
    return MockSMSProvider()
