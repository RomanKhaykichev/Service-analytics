"""
Access control helpers (subscription status). trial_ends_at = subscription end for all plans.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.deps import is_user_admin
from app.db import qname


def _as_utc_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def compute_subscription_days_left(trial_ends_at: Optional[datetime]) -> Optional[int]:
    """
    Remaining subscription days (admin column «Дней»).
    Same field for Trial 10, Month 5, Month 10 and Gold — not trial-plan-specific.
    """
    if trial_ends_at is None:
        return None
    end = _as_utc_aware(trial_ends_at) if isinstance(trial_ends_at, datetime) else None
    if end is None:
        return None
    days = (end.date() - date.today()).days
    return max(days, 0)


def compute_trial_days_left(trial_ends_at: Optional[datetime]) -> Optional[int]:
    """Backward-compatible alias for compute_subscription_days_left."""
    return compute_subscription_days_left(trial_ends_at)


def is_admin_subscription_status_active(
    user_id: UUID,
    db: Session,
    *,
    trial_ends_at: Optional[datetime],
) -> bool:
    """
    True when admin Users table column «Статус» shows green «Активен».
    Matches Admin.tsx badge: admin OR subscription_days_left > 0 (any tariff).
    """
    if is_user_admin(user_id, db):
        return True
    days_left = compute_subscription_days_left(trial_ends_at)
    return days_left is not None and days_left > 0


def is_subscription_status_active(
    user_id: UUID,
    db: Session,
    *,
    is_active: bool,
    trial_ends_at: Optional[datetime],
) -> bool:
    """
    True when admin Users table shows green «Активен» in column «Статус подписки».
    Applies equally to all tariffs: admin OR subscription_days_left > 0.
    """
    if not is_active:
        return False
    if is_user_admin(user_id, db):
        return True
    days_left = compute_subscription_days_left(trial_ends_at)
    return days_left is not None and days_left > 0


def is_user_active_in_admin_ui(
    user_id: UUID,
    db: Session,
    *,
    is_active: bool,
    trial_ends_at: Optional[datetime],
) -> bool:
    """Backward-compatible alias for is_subscription_status_active."""
    return is_subscription_status_active(
        user_id, db, is_active=is_active, trial_ends_at=trial_ends_at
    )


def subscription_active_reason(
    user_id: UUID,
    db: Session,
    *,
    is_active: bool,
    trial_ends_at: Optional[datetime],
) -> tuple[bool, str]:
    """Check whether sync/import is allowed; message for uzum_sync_log when skipped."""
    if not is_active:
        return False, "Аккаунт заблокирован"
    if is_user_admin(user_id, db):
        return True, ""
    if is_subscription_status_active(
        user_id, db, is_active=True, trial_ends_at=trial_ends_at
    ):
        return True, ""
    return False, "Подписка не активна"


def scheduled_uzum_sync_allowed(
    user_id: UUID,
    db: Session,
    *,
    is_active: bool,
    trial_ends_at: Optional[datetime],
) -> tuple[bool, str]:
    """
    Auto-sync (06:00 / 18:00): admin or «Активен» in admin «Статус подписки».
    «Не активен» on any tariff (Trial, Month 5, Month 10, Gold) → skip.
    """
    return subscription_active_reason(
        user_id, db, is_active=is_active, trial_ends_at=trial_ends_at
    )


def require_active_access(user_id: UUID, db: Session) -> None:
    """
    Deny when admin Users table would show «Не активен» in «Статус подписки».
    Admins (ADMIN_USER_IDS) always pass.
    """
    if is_user_admin(user_id, db):
        return

    row = db.execute(
        text(
            f"SELECT is_active, trial_ends_at FROM {qname('users')} WHERE id = CAST(:uid AS uuid)"
        ),
        {"uid": str(user_id)},
    ).fetchone()

    if not row:
        return

    is_active = bool(row[0]) if row[0] is not None else True
    trial_ends_at = row[1]

    if is_subscription_status_active(
        user_id, db, is_active=is_active, trial_ends_at=trial_ends_at
    ):
        return

    raise HTTPException(status_code=403, detail="Подписка не активна")


def count_uzum_api_users_with_active_status(db: Session) -> int:
    """
    Users with Uzum API key and green «Активен» in admin «Статус» column.
    Used for Active metric on admin Uzum sync logs tab.
    """
    rows = db.execute(
        text(
            f"""
            SELECT id, trial_ends_at
            FROM {qname("users")}
            WHERE uzum_seller_api_key IS NOT NULL
              AND trim(uzum_seller_api_key) <> ''
            """
        )
    ).fetchall()
    count = 0
    for row in rows:
        user_id = row[0]
        if not isinstance(user_id, UUID):
            user_id = UUID(str(user_id))
        if is_admin_subscription_status_active(
            user_id, db, trial_ends_at=row[1]
        ):
            count += 1
    return count
