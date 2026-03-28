"""
Pending registration draft rows (pre-verify): cleanup of expired records.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import qname


def cleanup_expired_pending(db: Session) -> int:
    """
    Delete pending registrations whose expires_at is in the past.
    Returns the number of rows deleted (may be 0).
    """
    result = db.execute(
        text(f"DELETE FROM {qname('pending_registrations')} WHERE expires_at < now()")
    )
    return int(result.rowcount or 0)
