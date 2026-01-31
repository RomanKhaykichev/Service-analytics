"""
Unified shop filter for seller-storage (app.fact_storage_snapshot.shop_raw).

- Source of shop list: only seller-storage (fact_storage_snapshot.shop_raw).
- Binding to sales/leftout/services: only via barcode_norm (fallback: normalize(barcode)).
- Use qname() and SET search_path so SQL never depends on current_schema=public.
"""

import re
from typing import Optional

from app.db import qname
from app.utils.barcode import barcode_norm_sql


def normalize_shop(shop: Optional[str]) -> Optional[str]:
    """
    Normalize shop name (seller-storage "Магазин" column) for consistent comparison.

    Same as backend comparison: upper(trim), collapse whitespace to single space.
    """
    if not shop or not str(shop).strip():
        return None
    s = str(shop).upper().strip()
    s = re.sub(r"\s+", " ", s)
    return s if s else None


def storage_barcode_filter_sql(outer_table_alias: str, prefix_and: bool = False) -> str:
    """
    Return SQL fragment for filtering by seller-storage shop (barcode set).

    Use when shop_norm is set. Caller must add params["shop_norm"] = shop_norm.

    Pattern: only rows where (outer_table.barcode_norm / barcode) exists in
    app.fact_storage_snapshot for the selected shop (shop_raw normalized).

    Returns:
        "EXISTS (SELECT 1 FROM app.fact_storage_snapshot fss WHERE ... = :shop_norm)"
        or "AND EXISTS (...)" if prefix_and=True (for appending to WHERE string).
    """
    alias = outer_table_alias.strip() or "t"
    fragment = f"""EXISTS (
                SELECT 1 FROM {qname("fact_storage_snapshot")} fss
                WHERE fss.user_id = {alias}.user_id
                  AND COALESCE(fss.barcode_norm, {barcode_norm_sql("fss.barcode")}) = COALESCE({alias}.barcode_norm, {barcode_norm_sql(f"{alias}.barcode")})
                  AND upper(regexp_replace(trim(COALESCE(fss.shop_raw, '')), '\\s+', ' ', 'g')) = :shop_norm
            )"""
    return f"AND {fragment}" if prefix_and else fragment


def shop_filter_condition(
    shop: Optional[str],
    shop_id: Optional[str],
    *,
    outer_table_alias: str = "fact_sales",
) -> tuple[str, dict]:
    """
    Return (shop_condition_sql, params_update) for WHERE clause.

    - If shop (string) is set: use storage barcode filter; params get shop_norm.
    - Else if shop_id (UUID) is set: use "{alias}.shop_id = CAST(:shop_id AS uuid)" (or "shop_id = ..." if alias empty).
    - Else: return ("", {}).

    Caller merges params_update into their params and appends shop_condition_sql to WHERE (join with " AND ").
    """
    shop_norm = normalize_shop(shop)
    if shop_norm:
        return storage_barcode_filter_sql(outer_table_alias), {"shop_norm": shop_norm}
    if shop_id:
        cond = f"{outer_table_alias}.shop_id = CAST(:shop_id AS uuid)" if outer_table_alias else "shop_id = CAST(:shop_id AS uuid)"
        return cond, {"shop_id": shop_id}
    return "", {}
