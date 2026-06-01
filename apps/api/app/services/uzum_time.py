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


def uz_calendar_day_start_ms(ts_ms: int) -> int:
    """Midnight at the start of that calendar day in Asia/Tashkent."""
    dt = ms_to_uz_datetime(ts_ms)
    start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(start.timestamp() * 1000)


def in_uz_calendar_range(
    ts_ms: Optional[int],
    date_from_ms: Optional[int],
    date_to_ms: Optional[int],
) -> bool:
    """Inclusive filter by calendar day in Uzbekistan (not raw instant edges)."""
    if date_from_ms is None and date_to_ms is None:
        return True
    if ts_ms is None:
        return False
    day = uz_calendar_day_start_ms(ts_ms)
    if date_from_ms is not None and day < uz_calendar_day_start_ms(date_from_ms):
        return False
    if date_to_ms is not None and day > uz_calendar_day_start_ms(date_to_ms):
        return False
    return True


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


def expense_cabinet_date_ms(ts_ms: Optional[int]) -> Optional[int]:
    """Сдвинуть dateService Open API на +1 календарный день (как «Дата списания» в Excel кабинета)."""
    if ts_ms is None:
        return None
    dt = ms_to_uz_datetime(ts_ms) + timedelta(days=1)
    return int(dt.timestamp() * 1000)


def sql_uz_calendar_date(column_sql: str) -> str:
    """PostgreSQL: timestamptz → calendar date in Asia/Tashkent (for GROUP BY / charts)."""
    return f"(({column_sql}) AT TIME ZONE '{UZ_TIMEZONE_NAME}')::date"


def sql_parse_expense_written_off_raw(column: str = "written_off_raw") -> str:
    """PostgreSQL CASE: «Дата списания» raw → timestamptz (calendar day in Uzbekistan)."""
    return f"""(
        CASE
            WHEN {column} ~ '^\\d{{4}}-\\d{{2}}-\\d{{2}}' THEN {column}::timestamptz
            WHEN {column} ~ '^\\d{{2}}\\.\\d{{2}}\\.\\d{{4}}\\s+\\d{{1,2}}:\\d{{2}}'
              THEN (to_timestamp(trim({column}), 'DD.MM.YYYY HH24:MI') AT TIME ZONE '{UZ_TIMEZONE_NAME}')
            WHEN {column} ~ '^\\d{{2}}\\.\\d{{2}}\\.\\d{{4}}'
              THEN (
                to_timestamp(
                  substring(trim({column}) from '^[0-9]{{2}}\\.[0-9]{{2}}\\.[0-9]{{4}}'),
                  'DD.MM.YYYY'
                ) AT TIME ZONE '{UZ_TIMEZONE_NAME}'
              )
            WHEN ({column} ~ '^\\d+(\\.\\d*)?$' OR {column} ~ '^\\d+,\\d*$')
                 AND replace({column}, ',', '.')::numeric > 0
              THEN (
                CASE
                  WHEN (
                    timestamp '1899-12-30'
                    + (replace({column}, ',', '.')::numeric * interval '1 day')
                  )::date < '2024-01-01'::date
                    THEN (
                      timestamp '1904-01-01'
                      + (replace({column}, ',', '.')::numeric * interval '1 day')
                    )::timestamptz
                  ELSE (
                    timestamp '1899-12-30'
                    + (replace({column}, ',', '.')::numeric * interval '1 day')
                  )::timestamptz
                END
              )
            ELSE NULL
        END
    )"""
