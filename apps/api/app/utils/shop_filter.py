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


def storage_barcode_filter_sql(
    outer_table_alias: str,
    prefix_and: bool = False,
    *,
    outer_barcode_norm_expr: Optional[str] = None,
) -> str:
    """
    Return SQL fragment for filtering by seller-storage shop (barcode set).

    Use when shop_norm is set. Caller must add params["shop_norm"] = shop_norm.

    Pattern: only rows where (outer_table.barcode_norm / barcode) exists in
    app.fact_storage_snapshot for the selected shop (shop_raw normalized).
    fact_storage_snapshot side: COALESCE(fss.barcode_norm, computed) so it works
    even if barcode_norm column is missing.

    If outer_barcode_norm_expr is set (e.g. for views without barcode_norm column),
    use it for the outer table side instead of COALESCE(alias.barcode_norm, computed).

    Returns:
        "EXISTS (SELECT 1 FROM app.fact_storage_snapshot fss WHERE ... = :shop_norm)"
        or "AND EXISTS (...)" if prefix_and=True (for appending to WHERE string).
    """
    alias = outer_table_alias.strip() or "t"
    outer_side = (
        outer_barcode_norm_expr
        if outer_barcode_norm_expr is not None
        else f"COALESCE({alias}.barcode_norm, {barcode_norm_sql(f'{alias}.barcode')})"
    )
    fragment = f"""EXISTS (
                SELECT 1 FROM {qname("fact_storage_snapshot")} fss
                WHERE fss.user_id = {alias}.user_id
                  AND COALESCE(fss.barcode_norm, {barcode_norm_sql("fss.barcode")}) = {outer_side}
                  AND upper(regexp_replace(trim(COALESCE(fss.shop_raw, '')), '\\s+', ' ', 'g')) = :shop_norm
            )"""
    return f"AND {fragment}" if prefix_and else fragment


def storage_barcode_filter_by_shop_id_sql(
    outer_table_alias: str,
    prefix_and: bool = False,
    *,
    outer_barcode_norm_expr: Optional[str] = None,
) -> str:
    """
    Return SQL fragment for filtering by shop_id: only rows whose barcode exists in
    fact_storage_snapshot for the selected shop_id (last storage snapshot per user).
    Caller must add params["shop_id"] = shop_id.
    Does NOT use shop_raw (use when filtering by dim_shop.shop_id).
    """
    alias = outer_table_alias.strip() or "t"
    outer_side = (
        outer_barcode_norm_expr
        if outer_barcode_norm_expr is not None
        else f"COALESCE({alias}.barcode_norm, {barcode_norm_sql(f'{alias}.barcode')})"
    )
    fragment = f"""EXISTS (
                SELECT 1 FROM {qname("fact_storage_snapshot")} fss
                INNER JOIN (
                    SELECT user_id, upload_batch_id
                    FROM (
                        SELECT user_id, upload_batch_id,
                               ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY loaded_at DESC NULLS LAST) AS rn
                        FROM {qname("fact_storage_snapshot")}
                    ) t WHERE rn = 1
                ) last ON fss.user_id = last.user_id AND fss.upload_batch_id = last.upload_batch_id
                WHERE fss.user_id = {alias}.user_id
                  AND COALESCE(fss.barcode_norm, {barcode_norm_sql("fss.barcode")}) = {outer_side}
                  AND fss.shop_id = CAST(:shop_id AS uuid)
            )"""
    return f"AND {fragment}" if prefix_and else fragment


def shop_filter_condition(
    shop: Optional[str],
    shop_id: Optional[str],
    *,
    outer_table_alias: str = "fact_sales",
    outer_barcode_norm_expr: Optional[str] = None,
) -> tuple[str, dict]:
    """
    Return (shop_condition_sql, params_update) for WHERE clause.

    - If shop (string) is set: use storage barcode filter; params get shop_norm.
      Pass outer_barcode_norm_expr for views/tables without barcode_norm (e.g. barcode_norm_sql("v.barcode")).
    - Else if shop_id (UUID) is set: use "{alias}.shop_id = CAST(:shop_id AS uuid)" (or "shop_id = ..." if alias empty).
    - Else: return ("", {}).

    Caller merges params_update into their params and appends shop_condition_sql to WHERE (join with " AND ").
    """
    shop_norm = normalize_shop(shop)
    if shop_norm:
        return (
            storage_barcode_filter_sql(
                outer_table_alias,
                prefix_and=False,
                outer_barcode_norm_expr=outer_barcode_norm_expr,
            ),
            {"shop_norm": shop_norm},
        )
    if shop_id:
        cond = f"{outer_table_alias}.shop_id = CAST(:shop_id AS uuid)" if outer_table_alias else "shop_id = CAST(:shop_id AS uuid)"
        return cond, {"shop_id": shop_id}
    return "", {}
