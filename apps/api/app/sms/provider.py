import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class SmsProvider(ABC):
    @abstractmethod
    def send_sms(self, phone: str, text: str) -> None:
        """Send SMS to normalized phone (e.g. +998901234567)."""


class ConsoleSmsProvider(SmsProvider):
    """Dev/test fallback when Eskiz env is missing."""

    def send_sms(self, phone: str, text: str) -> None:
        logger.warning("SMS (console fallback): to=%s text=%s", phone, text)
