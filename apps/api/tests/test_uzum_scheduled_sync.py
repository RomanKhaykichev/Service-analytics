"""Scheduled Uzum sync eligibility and logging."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import MagicMock, patch

from app.services.uzum_sync import _scheduled_sync_one_user


def test_inactive_status_skips_without_sync_log():
    uid = uuid4()
    db = MagicMock()
    stats = {"success": 0, "failed": 0, "skipped": 0}
    user = {
        "id": uid,
        "api_key": "secret",
        "is_active": True,
        "trial_ends_at": None,
        "phone": "+998901234567",
        "phone_verified_at": datetime.now(timezone.utc),
    }

    with patch(
        "app.services.uzum_sync.is_admin_subscription_status_active",
        return_value=False,
    ), patch("app.services.uzum_sync._insert_sync_log") as insert_log, patch(
        "app.services.uzum_sync.run_uzum_sync_for_user"
    ) as run_sync:
        status = _scheduled_sync_one_user(db, user, stats)

    assert status == "skipped"
    insert_log.assert_not_called()
    run_sync.assert_not_called()
    assert stats == {"success": 0, "failed": 0, "skipped": 0}


def test_active_status_runs_sync_and_logs_on_failure():
    uid = uuid4()
    db = MagicMock()
    stats = {"success": 0, "failed": 0, "skipped": 0}
    user = {
        "id": uid,
        "api_key": "secret",
        "is_active": True,
        "trial_ends_at": datetime.now(timezone.utc) + timedelta(days=5),
        "phone": "+998901234567",
        "phone_verified_at": datetime.now(timezone.utc),
    }

    with patch(
        "app.services.uzum_sync.is_admin_subscription_status_active",
        return_value=True,
    ), patch(
        "app.services.uzum_sync.is_phone_verified_for_sync",
        return_value=(True, ""),
    ), patch(
        "app.services.uzum_sync.run_uzum_sync_for_user",
        return_value={"status": "failed", "log_id": "log-1"},
    ):
        status = _scheduled_sync_one_user(db, user, stats)

    assert status == "failed"
    assert stats["failed"] == 1
