"""
Minimal tests for /api/kpi/summary date-range behaviour.

- period=30d: uses period to compute date range.
- date_from & date_to: explicit range (priority over period).
- date_from > date_to: returns 400.
"""
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app
from app.deps import require_user
from app.routes.kpi import period_range
from datetime import datetime


def test_period_range_30d():
    """period=30d gives date_to = data_end_date, date_from = data_end_date - 29 days."""
    end = datetime(2025, 11, 30).date()
    pr = period_range("30d", end)
    assert pr["code"] == "30d"
    assert pr["date_to"] == "2025-11-30"
    assert pr["date_from"] == "2025-11-01"


def test_period_range_all():
    """period=all gives date_from=None, date_to=data_end_date."""
    end = datetime(2025, 11, 30).date()
    pr = period_range("all", end)
    assert pr["code"] == "all"
    assert pr["date_to"] == "2025-11-30"
    assert pr["date_from"] is None


def test_kpi_summary_date_from_after_date_to_returns_400():
    """GET /api/kpi/summary?date_from=2025-11-30&date_to=2025-11-01 returns 400."""
    client = TestClient(app)
    user_id = uuid4()
    app.dependency_overrides[require_user] = lambda: user_id
    try:
        r = client.get("/api/kpi/summary?date_from=2025-11-30&date_to=2025-11-01")
        assert r.status_code == 400
        assert "date_from" in r.json().get("detail", "").lower() or "date" in r.json().get("detail", "").lower()
    finally:
        app.dependency_overrides.pop(require_user, None)


def test_kpi_summary_invalid_date_format_returns_400():
    """GET /api/kpi/summary?date_from=invalid&date_to=2025-11-30 returns 400."""
    client = TestClient(app)
    user_id = uuid4()
    app.dependency_overrides[require_user] = lambda: user_id
    try:
        r = client.get("/api/kpi/summary?date_from=invalid&date_to=2025-11-30")
        assert r.status_code == 400
    finally:
        app.dependency_overrides.pop(require_user, None)
