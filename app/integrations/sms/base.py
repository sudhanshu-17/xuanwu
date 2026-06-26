"""SMS provider interface shared by every concrete provider."""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class SMSMessage:
    to: str  # destination number in E.164 form
    body: str


@runtime_checkable
class SMSProvider(Protocol):
    """Sends one message. Implementations raise on transient failure so the
    Celery task can retry."""

    def send(self, message: SMSMessage) -> None: ...
