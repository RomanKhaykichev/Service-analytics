"""Subscription status rules — admin column «Статус подписки» for all tariffs."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import MagicMock, patch

from app.auth.access import (
    compute_subscription_days_left,
    count_uzum_api_users_with_active_status,
    is_admin_subscription_status_active,
    is_subscription_status_active,
    scheduled_uzum_sync_allowed,
    subscription_active_reason,
)


def test_subscription_days_left_none_when_no_end_date():
    assert compute_subscription_days_left(None) is None


def test_subscription_days_left_positive():
    future = datetime.now(timezone.utc) + timedelta(days=5)
    assert compute_subscription_days_left(future) == 5


def test_subscription_days_left_zero_when_expired():
    past = datetime.now(timezone.utc) - timedelta(days=3)
    assert compute_subscription_days_left(past) == 0


def test_inactive_when_no_subscription_end():
    uid = uuid4()
    db = MagicMock()
    assert not is_subscription_status_active(uid, db, is_active=True, trial_ends_at=None)


def test_inactive_when_subscription_expired():
    uid = uuid4()
    db = MagicMock()
    past = datetime.now(timezone.utc) - timedelta(days=1)
    assert not is_subscription_status_active(uid, db, is_active=True, trial_ends_at=past)


def test_active_when_subscription_remaining():
    uid = uuid4()
    db = MagicMock()
    future = datetime.now(timezone.utc) + timedelta(days=10)
    assert is_subscription_status_active(uid, db, is_active=True, trial_ends_at=future)


def test_month10_active_with_days_left():
    """Paid Month 10 with valid subscription period → «Активен»."""
    uid = uuid4()
    db = MagicMock()
    future = datetime.now(timezone.utc) + timedelta(days=20)
    assert is_subscription_status_active(uid, db, is_active=True, trial_ends_at=future)


def test_month10_inactive_when_subscription_expired():
    """Paid Month 10 with expired subscription → «Не активен», no auto-sync."""
    uid = uuid4()
    db = MagicMock()
    past = datetime.now(timezone.utc) - timedelta(days=1)
    ok, reason = scheduled_uzum_sync_allowed(
        uid, db, is_active=True, trial_ends_at=past
    )
    assert not ok
    assert reason == "Подписка не активна"


def test_admin_status_column_active_for_admin():
    uid = uuid4()
    db = MagicMock()
    with patch("app.auth.access.is_user_admin", return_value=True):
        assert is_admin_subscription_status_active(uid, db, trial_ends_at=None)


def test_admin_status_column_inactive_when_no_subscription_end():
    uid = uuid4()
    db = MagicMock()
    with patch("app.auth.access.is_user_admin", return_value=False):
        assert not is_admin_subscription_status_active(uid, db, trial_ends_at=None)


def test_scheduled_sync_blocked_when_status_inactive():
    uid = uuid4()
    db = MagicMock()
    ok, reason = scheduled_uzum_sync_allowed(
        uid, db, is_active=True, trial_ends_at=None
    )
    assert not ok
    assert reason == "Подписка не активна"


def test_count_uzum_api_users_with_active_status():
    db = MagicMock()
    uid_active = uuid4()
    uid_inactive = uuid4()
    future = datetime.now(timezone.utc) + timedelta(days=5)
    db.execute.return_value.fetchall.return_value = [
        (uid_active, future),
        (uid_inactive, None),
    ]

    def _status_active(user_id, _db, *, trial_ends_at):
        return trial_ends_at is not None

    with patch(
        "app.auth.access.is_admin_subscription_status_active",
        side_effect=_status_active,
    ):
        assert count_uzum_api_users_with_active_status(db) == 1


def test_subscription_blocked_when_account_disabled():
    uid = uuid4()
    db = MagicMock()
    future = datetime.now(timezone.utc) + timedelta(days=10)
    ok, reason = subscription_active_reason(
        uid, db, is_active=False, trial_ends_at=future
    )
    assert not ok
    assert reason == "Аккаунт заблокирован"
