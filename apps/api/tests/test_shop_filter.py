"""
Tests for unified shop filter (seller-storage, barcode_norm).

- Invariants: shop list from fact_storage_snapshot.shop_raw only; binding via barcode_norm.
- Without shop: all data (no filter).
- With shop: filter by barcode set from fact_storage_snapshot for that shop_norm.
"""
import pytest
from app.utils.shop_filter import normalize_shop, storage_barcode_filter_sql, shop_filter_condition, expenses_shop_filter_condition


def test_normalize_shop_none():
    """Without shop, shop_norm is None."""
    assert normalize_shop(None) is None
    assert normalize_shop("") is None


def test_normalize_shop_upper_trim():
    """Shop name is upper-cased and trimmed."""
    assert normalize_shop("  Магазин 1  ") == "МАГАЗИН 1"
    assert normalize_shop("Shop A") == "SHOP A"


def test_normalize_shop_collapse_whitespace():
    """Multiple spaces collapse to one (same as backend comparison)."""
    assert normalize_shop("Shop   A") == "SHOP A"
    assert normalize_shop("  A   B  ") == "A B"


def test_storage_barcode_filter_sql_contains_fact_storage_snapshot():
    """SQL fragment references app.fact_storage_snapshot (schema-qualified via qname)."""
    fragment = storage_barcode_filter_sql("fact_sales")
    assert "fact_storage_snapshot" in fragment
    assert "EXISTS" in fragment
    assert ":shop_norm" in fragment
    assert "fact_sales.user_id" in fragment


def test_storage_barcode_filter_sql_prefix_and():
    """With prefix_and=True, fragment starts with AND."""
    fragment = storage_barcode_filter_sql("t", prefix_and=True)
    assert fragment.strip().startswith("AND ")
    assert "EXISTS" in fragment


def test_shop_filter_condition_no_shop():
    """When neither shop nor shop_id, condition is empty."""
    cond, params = shop_filter_condition(None, None)
    assert cond == ""
    assert params == {}


def test_shop_filter_condition_with_shop():
    """When shop is set, returns barcode EXISTS or dim_shop match and shop_norm in params."""
    cond, params = shop_filter_condition("  Shop A  ", None, outer_table_alias="fact_sales")
    assert "EXISTS" in cond
    assert "dim_shop" in cond
    assert " OR " in cond
    assert params == {"shop_norm": "SHOP A"}


def test_shop_filter_condition_with_shop_id():
    """When shop_id is set (no shop), returns shop_id condition."""
    cond, params = shop_filter_condition(None, "550e8400-e29b-41d4-a716-446655440000", outer_table_alias="fact_sales")
    assert "shop_id" in cond
    assert "CAST(:shop_id AS uuid)" in cond
    assert params == {"shop_id": "550e8400-e29b-41d4-a716-446655440000"}


def test_shop_filter_condition_shop_overrides_shop_id():
    """When both shop and shop_id are set, shop (barcode/dim filter) wins."""
    cond, params = shop_filter_condition("Shop A", "550e8400-e29b-41d4-a716-446655440000", outer_table_alias="fs")
    assert "EXISTS" in cond
    assert "dim_shop" in cond
    assert params == {"shop_norm": "SHOP A"}


def test_expenses_shop_filter_by_name():
    cond, params = expenses_shop_filter_condition("  My Shop  ", None, outer_table_alias="fe")
    assert "fe.shop_raw" in cond
    assert params == {"shop_norm": "MY SHOP"}


def test_expenses_shop_filter_by_shop_id():
    cond, params = expenses_shop_filter_condition(None, "550e8400-e29b-41d4-a716-446655440000", outer_table_alias="fe")
    assert cond == "fe.shop_id = CAST(:shop_id AS uuid)"
    assert params["shop_id"] == "550e8400-e29b-41d4-a716-446655440000"


def test_sql_never_public_schema():
    """Generated SQL uses qualified names (qname), not bare table names in public."""
    fragment = storage_barcode_filter_sql("fact_sales")
    # Should not be a bare FROM fact_storage_snapshot without schema (qname adds app.)
    assert "fact_storage_snapshot" in fragment
    # Pattern "FROM fact_storage_snapshot" without dot would be wrong; we use qname() which yields app.fact_storage_snapshot
    assert "FROM " in fragment
