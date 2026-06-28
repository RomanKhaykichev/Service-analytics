"""Tests for Uzum sync default date ranges by plan."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.services.uzum_sync import resolve_uzum_sync_date_range, user_uses_trial_sync_window


def _mock_db_with_plan(plan: str):
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = (plan,)
    return db


@patch("app.services.uzum_sync.is_user_admin", return_value=False)
@patch("app.services.uzum_sync.uz_now")
def test_trial_sync_uses_last_60_days(mock_uz_now, _mock_admin):
    mock_uz_now.return_value = datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)
    user_id = uuid4()
    db = _mock_db_with_plan("trial")

    assert user_uses_trial_sync_window(db, user_id) is True

    start, end = resolve_uzum_sync_date_range(
        db,
        user_id,
        date_from="2026-01-01",
        date_to="2026-05-28",
    )
    assert start == "2026-03-30"
    assert end == "2026-05-28"


@patch("app.services.uzum_sync.is_user_admin", return_value=False)
@patch("app.services.uzum_sync.uz_now")
def test_paid_plan_sync_uses_ytd_when_dates_omitted(mock_uz_now, _mock_admin):
    mock_uz_now.return_value = datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)
    user_id = uuid4()
    db = _mock_db_with_plan("month_5")

    assert user_uses_trial_sync_window(db, user_id) is False

    start, end = resolve_uzum_sync_date_range(db, user_id)
    assert start == "2026-01-01"
    assert end == "2026-05-28"


@patch("app.services.uzum_sync.is_user_admin", return_value=False)
@patch("app.services.uzum_sync.uz_now")
def test_paid_plan_respects_explicit_date_from(mock_uz_now, _mock_admin):
    mock_uz_now.return_value = datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)
    user_id = uuid4()
    db = _mock_db_with_plan("gold")

    start, end = resolve_uzum_sync_date_range(
        db,
        user_id,
        date_from="2026-03-01",
        date_to="2026-05-28",
    )
    assert start == "2026-03-01"
    assert end == "2026-05-28"


@patch("app.services.uzum_sync.is_user_admin", return_value=True)
@patch("app.services.uzum_sync.uz_now")
def test_admin_on_trial_plan_uses_ytd(mock_uz_now, _mock_admin):
    mock_uz_now.return_value = datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)
    user_id = uuid4()
    db = _mock_db_with_plan("trial")

    assert user_uses_trial_sync_window(db, user_id) is False

    start, end = resolve_uzum_sync_date_range(
        db,
        user_id,
        date_from="2026-01-01",
        date_to="2026-05-28",
    )
    assert start == "2026-01-01"
    assert end == "2026-05-28"
