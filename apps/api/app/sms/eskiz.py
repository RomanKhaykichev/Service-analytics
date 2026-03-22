"""
Eskiz.uz SMS API: POST /auth/login, POST /message/sms/send.
See https://notify.eskiz.uz/api (Postman docs).
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

import requests
from requests import HTTPError

from app.settings import Settings
from app.sms.provider import SmsProvider

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_cached_token: Optional[str] = None
_cached_token_type: str = "Bearer"
_cached_expires_at_monotonic: float = 0.0

# Eskiz token TTL ~24h; refresh early
_CACHE_TTL_SEC = 50 * 60


def _invalidate_token_cache() -> None:
    global _cached_token, _cached_expires_at_monotonic
    _cached_token = None
    _cached_expires_at_monotonic = 0.0


def _login(settings: Settings) -> tuple[str, str]:
    url = f"{settings.ESKIZ_BASE_URL}/auth/login"
    r = requests.post(
        url,
        json={"email": settings.ESKIZ_EMAIL, "password": settings.ESKIZ_PASSWORD},
        timeout=30,
        headers={"Content-Type": "application/json"},
    )
    r.raise_for_status()
    data = r.json()
    inner = data.get("data") or {}
    token = inner.get("token")
    if not token:
        raise RuntimeError(f"Eskiz login: no token in response: {data}")
    token_type = (data.get("token_type") or "Bearer").strip()
    return str(token), token_type


def _refresh_token(settings: Settings, current_token: str, token_type: str) -> tuple[str, str]:
    url = f"{settings.ESKIZ_BASE_URL}/auth/refresh"
    auth = f"{token_type} {current_token}"
    r = requests.patch(
        url,
        timeout=30,
        headers={"Authorization": auth},
    )
    r.raise_for_status()
    data = r.json()
    inner = data.get("data") or {}
    token = inner.get("token")
    if not token:
        raise RuntimeError(f"Eskiz refresh: no token: {data}")
    return str(token), (data.get("token_type") or token_type).strip()


def get_eskiz_bearer(settings: Settings) -> tuple[str, str]:
    global _cached_token, _cached_token_type, _cached_expires_at_monotonic
    with _lock:
        now = time.monotonic()
        if _cached_token and now < _cached_expires_at_monotonic:
            return _cached_token, _cached_token_type
        token, ttype = _login(settings)
        _cached_token = token
        _cached_token_type = ttype
        _cached_expires_at_monotonic = now + _CACHE_TTL_SEC
        return token, ttype


def _send_payload(settings: Settings, token: str, token_type: str, phone_digits: str, text: str) -> dict[str, Any]:
    url = f"{settings.ESKIZ_BASE_URL}/message/sms/send"
    body = {
        "mobile_phone": phone_digits,
        "message": text,
        "from": settings.ESKIZ_FROM,
    }
    auth = f"{token_type} {token}"
    r = requests.post(
        url,
        json=body,
        timeout=30,
        headers={"Authorization": auth, "Content-Type": "application/json"},
    )
    if r.status_code == 401:
        raise _Unauthorized()
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict) and data.get("status") not in (None, "success", "ok", 200):
        # some APIs return status/message
        if str(data.get("status", "")).lower() in ("error", "failed"):
            raise RuntimeError(f"Eskiz send error: {data}")
    return data if isinstance(data, dict) else {}


class _Unauthorized(Exception):
    pass


class EskizSmsProvider(SmsProvider):
    def __init__(self, settings: Settings):
        self._settings = settings

    def send_sms(self, phone: str, text: str) -> None:
        digits = "".join(c for c in phone if c.isdigit())
        if digits.startswith("998"):
            mobile = digits
        elif len(digits) == 9:
            mobile = "998" + digits
        else:
            mobile = digits

        last_err: Optional[Exception] = None
        for attempt in range(2):
            try:
                token, ttype = get_eskiz_bearer(self._settings)
                _send_payload(self._settings, token, ttype, mobile, text)
                return
            except _Unauthorized:
                _invalidate_token_cache()
                last_err = None
                continue
            except Exception as e:
                last_err = e
                if attempt == 0 and "401" in str(e):
                    _invalidate_token_cache()
                    continue
                raise
        if last_err:
            raise last_err
