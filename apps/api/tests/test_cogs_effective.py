"""Tests for effective unit COGS SQL helpers (Profiboard override)."""

from app.db import qname
from app.utils.metrics import (
    sql_cogs_line_amount,
    sql_effective_unit_cogs,
    sql_effective_unit_cogs_as_of,
    sql_latest_profiboard_unit_cogs,
    sql_sales_barcode_norm,
    sql_stock_cogs_line_amount,
)


def test_sql_effective_unit_cogs_contains_history_lookup():
    expr = sql_effective_unit_cogs("fs")
    assert qname("manual_product_cogs_history") in expr
    assert "effective_from" in expr
    assert "fs.user_id" in expr
    assert "fs.cogs_sum" in expr


def test_sql_cogs_line_amount_uses_effective_unit():
    expr = sql_cogs_line_amount("fs")
    assert "manual_product_cogs_history" in expr
    assert "returns_qty" in expr


def test_sql_sales_barcode_norm_strips_dot_zero():
    expr = sql_sales_barcode_norm("fs")
    assert "fs.barcode_norm" in expr
    assert ".0" in expr


def test_sql_effective_unit_cogs_no_alias_defaults_to_fs():
    expr = sql_effective_unit_cogs()
    assert "fs.user_id" in expr
    assert "fs.barcode_norm" in expr
    assert "fs.cogs_sum" in expr


def test_sql_effective_unit_cogs_kpi_alias():
    expr = sql_effective_unit_cogs("fact_sales")
    assert "fact_sales.user_id" in expr
    assert "fact_sales.barcode_norm" in expr


def test_sql_stock_cogs_line_amount_uses_latest_profiboard():
    expr = sql_stock_cogs_line_amount("lo")
    assert "manual_product_cogs_history" in expr
    assert "manual_product_cogs" in expr
    assert "lo.in_sale_qty" in expr
    assert "effective_from DESC" in expr
    assert "effective_from <=" not in expr


def test_sql_fbs_stock_cogs_line_amount_uses_fbs_qty():
    from app.utils.metrics import sql_fbs_stock_cogs_line_amount

    expr = sql_fbs_stock_cogs_line_amount("lo")
    assert "manual_product_cogs_history" in expr
    assert "lo.fbs_qty" in expr
    assert "lo.in_sale_qty" not in expr
    assert "effective_from DESC" in expr


def test_sql_latest_profiboard_unit_cogs_uses_alias():
    expr = sql_latest_profiboard_unit_cogs("lo")
    assert "lo.user_id" in expr
    assert "lo.cost_sum" in expr
    assert "ORDER BY pb.effective_from DESC" in expr


def test_sql_effective_unit_cogs_as_of_uses_alias():
    expr = sql_effective_unit_cogs_as_of("lo", "CURRENT_DATE")
    assert "lo.user_id" in expr
    assert "lo.barcode_norm" in expr
    assert "lo.cost_sum" in expr
