"""Date/time helpers for Uzum Seller API — always Uzbekistan (Asia/Tashkent, GMT+5)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from zoneinfo import ZoneInfo

# Uzbekistan standard time (no DST): UTC+5
UZ_TZ = ZoneInfo("Asia/Tashkent")
UZ_TIMEZONE_NAME = "Asia/Tashkent"
UZ_UTC_OFFSET = "+05:00"

DATETIME_DISPLAY_FMT = "%d.%m.%Y %H:%M"
CALENDAR_DATE_FMT = "%Y-%m-%d"


def uz_now() -> datetime:
    return datetime.now(UZ_TZ)


def ms_to_uz_datetime(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=UZ_TZ)


def normalize_epoch_ms(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        ms = int(value)
    except (TypeError, ValueError):
        return None
    if ms < 10_000_000_000:
        ms *= 1000
    elif ms > 10_000_000_000_000:
        ms //= 1000
    return ms


def parse_to_epoch_ms(value: Any) -> Optional[int]:
    """Unix ms / seconds or ISO string → epoch milliseconds (absolute instant)."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return normalize_epoch_ms(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        normalized = text.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UZ_TZ)
        return int(dt.timestamp() * 1000)
    except ValueError:
        return None


def format_datetime(value: Any) -> str:
    """API timestamp → display string in Uzbekistan local time."""
    if value is None or value == "":
        return ""
    ms = normalize_epoch_ms(value)
    if ms is not None:
        try:
            return ms_to_uz_datetime(ms).strftime(DATETIME_DISPLAY_FMT)
        except (TypeError, ValueError, OSError):
            return str(value)
    text = str(value)
    try:
        normalized = text.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UZ_TZ)
        else:
            dt = dt.astimezone(UZ_TZ)
        return dt.strftime(DATETIME_DISPLAY_FMT)
    except ValueError:
        return text


def calendar_date_to_epoch_ms(
    date_str: Optional[str], *, end_of_day: bool = False
) -> Optional[int]:
    """Calendar YYYY-MM-DD as a day boundary in Uzbekistan (for API dateFrom/dateTo)."""
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str.strip(), CALENDAR_DATE_FMT)
        if end_of_day:
            dt = dt.replace(hour=23, minute=59, second=59, microsecond=999000)
        else:
            dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        return int(dt.replace(tzinfo=UZ_TZ).timestamp() * 1000)
    except ValueError:
        return None


def last_n_days_range_ms(days: int) -> tuple[int, int]:
    """Inclusive calendar window [today - days, today] in Uzbekistan."""
    now = uz_now()
    end_dt = now.replace(hour=23, minute=59, second=59, microsecond=999000)
    start_dt = (now - timedelta(days=days)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return int(start_dt.timestamp() * 1000), int(end_dt.timestamp() * 1000)


def timezone_metadata() -> dict[str, str]:
    return {
        "timezone": UZ_TIMEZONE_NAME,
        "utc_offset": UZ_UTC_OFFSET,
    }
