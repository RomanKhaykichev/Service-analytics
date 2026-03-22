"""
Access control helpers (trial / subscription). Extend later for paid status and grace period.
"""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.deps import is_user_admin
from app.db import qname


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def require_active_access(user_id: UUID, db: Session) -> None:
    """
    Deny non-admin users whose trial has ended (trial_ends_at set and not after now).
    Admins (ADMIN_USER_IDS) always pass.
    """
    if is_user_admin(user_id, db):
        return

    row = db.execute(
        text(
            f"SELECT trial_ends_at FROM {qname('users')} WHERE id = CAST(:uid AS uuid)"
        ),
        {"uid": str(user_id)},
    ).fetchone()

    if not row:
        return

    trial_ends_at = row[0]
    if trial_ends_at is None:
        return

    end = _as_utc_aware(trial_ends_at) if isinstance(trial_ends_at, datetime) else None
    if end is None:
        return

    if end <= _now_utc():
        raise HTTPException(status_code=403, detail="Trial expired")
