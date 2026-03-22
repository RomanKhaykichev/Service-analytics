"""
Phone OTP: normalization, hashing, rate limits, Eskiz send.
"""
from __future__ import annotations

import hashlib
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

from app.db import qname
from app.models import VerificationCode
from app.models.verification_code import VerificationChannel
from app.settings import get_settings
from app.sms import get_sms_provider

logger = logging.getLogger(__name__)

OTP_TTL_MIN = 5
SEND_WINDOW_MIN = 15
MAX_SENDS_PER_WINDOW = 3
MAX_VERIFY_FAILS_PER_WINDOW = 5


def normalize_uz_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 9:
        return "+998" + digits
    if digits.startswith("998") and len(digits) == 12:
        return "+" + digits
    if len(digits) >= 9 and phone.strip().startswith("+"):
        return "+" + digits
    raise ValueError("Invalid phone number")


def mask_phone(phone_norm: str) -> str:
    p = phone_norm.strip()
    if len(p) <= 6:
        return "***"
    return p[:5] + " *** ** " + p[-2:]


def otp_hash(code: str) -> str:
    secret = get_settings().OTP_SECRET
    return hashlib.sha256((secret + code).encode("utf-8")).hexdigest()


def generate_otp_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def count_recent_sends(db: Session, destination_norm: str) -> int:
    since = _now() - timedelta(minutes=SEND_WINDOW_MIN)
    n = (
        db.query(func.count(VerificationCode.id))
        .filter(
            VerificationCode.destination == destination_norm,
            or_(
                VerificationCode.channel == VerificationChannel.SMS,
                VerificationCode.channel == "sms",
            ),
            VerificationCode.created_at >= since,
        )
        .scalar()
    )
    return int(n or 0)


def count_recent_verify_fails(db: Session, phone_norm: str) -> int:
    since = _now() - timedelta(minutes=SEND_WINDOW_MIN)
    r = db.execute(
        text(
            f"""
            SELECT count(*) FROM {qname('otp_attempts')}
            WHERE phone_normalized = :ph
              AND kind = 'verify_fail'
              AND created_at >= :since
            """
        ),
        {"ph": phone_norm, "since": since},
    ).scalar()
    return int(r or 0)


def record_verify_fail(db: Session, user_id: UUID | None, phone_norm: str) -> None:
    db.execute(
        text(
            f"""
            INSERT INTO {qname('otp_attempts')} (user_id, phone_normalized, kind, created_at)
            VALUES (CAST(:uid AS uuid), :ph, 'verify_fail', now())
            """
        ),
        {"uid": str(user_id) if user_id else None, "ph": phone_norm},
    )


def assert_send_rate_limit(db: Session, destination_norm: str) -> None:
    if count_recent_sends(db, destination_norm) >= MAX_SENDS_PER_WINDOW:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=429,
            detail="Too many verification code requests. Try again later.",
        )


def assert_verify_fail_rate_limit(db: Session, phone_norm: str) -> None:
    if count_recent_verify_fails(db, phone_norm) >= MAX_VERIFY_FAILS_PER_WINDOW:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=429,
            detail="Too many invalid code attempts. Try again later.",
        )


def create_sms_verification(
    db: Session,
    user_id: UUID,
    destination_norm: str,
    code_plain: str,
) -> VerificationCode:
    expires = _now() + timedelta(minutes=OTP_TTL_MIN)
    vc = VerificationCode(
        user_id=user_id,
        channel=VerificationChannel.SMS,
        destination=destination_norm,
        code_hash=otp_hash(code_plain),
        expires_at=expires,
        consumed_at=None,
    )
    db.add(vc)
    return vc


def send_registration_otp_sms(destination_norm: str, code_plain: str) -> None:
    settings = get_settings()
    text_msg = f"PROFiboard: kod podtverzhdeniya {code_plain}"
    if settings.SMS_DEBUG_LOG_CODE:
        logger.warning("SMS OTP (debug log): phone=%s code=%s", destination_norm, code_plain)
    provider = get_sms_provider()
    provider.send_sms(destination_norm, text_msg)
