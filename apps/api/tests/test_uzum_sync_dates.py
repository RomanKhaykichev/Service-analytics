"""Tests for Uzum sync default date ranges by plan."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.services.uzum_sync import (
    resolve_sync_fetch_dates,
    resolve_uzum_sync_date_range,
    user_has_prior_successful_api_sync,
    user_uses_trial_sync_window,
)


def _mock_db_with_plan(plan: str, *, prior_api_success: bool = False):
    db = MagicMock()
    if prior_api_success:
        db.execute.return_value.fetchone.side_effect = [
            (1,),  # user_has_prior_successful_api_sync
            (plan,),  # resolve_uzum_sync_date_range plan lookup when needed
        ]
    else:
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


@patch("app.services.uzum_sync.user_has_prior_successful_api_sync", return_value=True)
@patch("app.services.uzum_sync.is_user_admin", return_value=False)
@patch("app.services.uzum_sync.uz_now")
def test_incremental_fetch_dates_after_prior_api_sync(mock_uz_now, _mock_admin, _mock_prior):
    mock_uz_now.return_value = datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)
    user_id = uuid4()
    db = MagicMock()

    dates = resolve_sync_fetch_dates(db, user_id)

    assert dates.mode == "incremental"
    assert dates.sales_from == "2026-04-29"
    assert dates.sales_to == "2026-05-28"
    assert dates.expenses_from == "2026-05-27"
    assert dates.expenses_to == "2026-05-28"
    assert dates.sales_replace_from == dates.sales_from
    assert dates.expenses_replace_from == dates.expenses_from


@patch("app.services.uzum_sync.user_has_prior_successful_api_sync", return_value=False)
@patch("app.services.uzum_sync.is_user_admin", return_value=False)
@patch("app.services.uzum_sync.uz_now")
def test_first_api_sync_stays_full_for_trial(mock_uz_now, _mock_admin, _mock_prior):
    mock_uz_now.return_value = datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)
    user_id = uuid4()
    db = _mock_db_with_plan("trial")

    dates = resolve_sync_fetch_dates(db, user_id)

    assert dates.mode == "full"
    assert dates.sales_from == "2026-03-30"
    assert dates.expenses_from == "2026-03-30"


@patch("app.services.uzum_sync.user_has_prior_successful_api_sync", return_value=True)
@patch("app.services.uzum_sync.uz_now")
def test_admin_force_full_sync_uses_ytd(mock_uz_now, _mock_prior):
    mock_uz_now.return_value = datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)
    user_id = uuid4()
    db = MagicMock()

    dates = resolve_sync_fetch_dates(db, user_id, force_full_sync=True)

    assert dates.mode == "full"
    assert dates.sales_from == "2026-01-01"
    assert dates.sales_to == "2026-05-28"
    assert dates.expenses_from == "2026-01-01"


def test_user_has_prior_successful_api_sync_true_when_row_exists():
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = (1,)
    assert user_has_prior_successful_api_sync(db, uuid4()) is True

