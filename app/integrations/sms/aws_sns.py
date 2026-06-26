"""AWS SNS SMS provider (synchronous boto3 client).

Credentials are resolved from the standard AWS chain (environment, instance
profile, …); only the region is configured here.
"""

from app.core.config import settings
from app.integrations.sms.base import SMSMessage


class AWSSNSProvider:
    def send(self, message: SMSMessage) -> None:
        import boto3

        client = boto3.client("sns", region_name=settings.aws_region)
        client.publish(PhoneNumber=message.to, Message=message.body)
