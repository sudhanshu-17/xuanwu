"""Twilio Programmable SMS provider (synchronous SDK)."""

from app.core.config import settings
from app.integrations.sms.base import SMSMessage


class TwilioSMSProvider:
    def send(self, message: SMSMessage) -> None:
        from twilio.rest import Client

        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        client.messages.create(
            to=message.to,
            from_=settings.twilio_from_number,
            body=message.body,
        )
