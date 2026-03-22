from app.settings import get_settings
from app.sms.provider import ConsoleSmsProvider, SmsProvider
from app.sms.eskiz import EskizSmsProvider


def get_sms_provider() -> SmsProvider:
    s = get_settings()
    devish = s.APP_ENV.lower() in ("dev", "development", "test")
    if s.ESKIZ_EMAIL and s.ESKIZ_PASSWORD and s.ESKIZ_FROM:
        return EskizSmsProvider(s)
    if devish:
        return ConsoleSmsProvider()
    raise RuntimeError(
        "SMS is not configured: set ESKIZ_EMAIL, ESKIZ_PASSWORD, ESKIZ_FROM for production"
    )
