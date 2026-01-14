from datetime import date, timedelta
from typing import Tuple, Optional
from uuid import UUID


def parse_period(period: str) -> Tuple[date, date, str]:
    """
    Parse period string to date range.
    Returns: (date_from, date_to, code)
    """
    today = date.today()
    
    if period == "7d":
        date_from = today - timedelta(days=7)
        return date_from, today, "7d"
    elif period == "30d":
        date_from = today - timedelta(days=30)
        return date_from, today, "30d"
    elif period == "60d":
        date_from = today - timedelta(days=60)
        return date_from, today, "60d"
    elif period == "90d":
        date_from = today - timedelta(days=90)
        return date_from, today, "90d"
    elif period == "all":
        date_from = date(1900, 1, 1)
        return date_from, today, "all"
    else:
        raise ValueError(f"Invalid period: {period}. Must be one of: 7d, 30d, 60d, 90d, all")


def normalize_shop_id(shop_id: Optional[str]) -> Optional[str]:
    """
    Validate shop_id UUID format if provided.
    Returns normalized UUID string or None.
    """
    if shop_id is None or shop_id == "":
        return None
    
    try:
        # Validate UUID format
        uuid_obj = UUID(shop_id)
        return str(uuid_obj)
    except ValueError:
        raise ValueError(f"Invalid shop_id format (must be UUID): {shop_id}")
