"""
Common metrics calculation utilities.
Shared between KPI and Charts endpoints to ensure consistency.
"""
from typing import Dict


def get_status_conditions() -> Dict[str, str]:
    """
    Get SQL status conditions used in KPI calculations.
    Returns the same conditions for both KPI and Charts to ensure consistency.
    
    Returns:
        dict with keys: 'processing', 'completed', 'cancelled', 'revenue'
    """
    return {
        'processing': "lower(trim(status)) = 'в обработке'",
        'completed': "lower(trim(status)) IN ('завершен', 'завершён')",
        'cancelled': "lower(trim(status)) IN ('отменен', 'отменён')",
        'revenue': "(lower(trim(status)) IN ('завершен', 'завершён') OR lower(trim(status)) = 'в обработке')",
    }


def get_sales_metrics_sql(
    table_alias: str = ""
) -> Dict[str, str]:
    """
    Generate SQL expressions for sales metrics using the same formulas as KPI.
    
    These expressions are used in SELECT with GROUP BY to aggregate metrics by time period.
    The grouping is done in the calling query, not in these expressions.
    
    Args:
        table_alias: Table alias prefix (e.g., "fs." or "")
    
    Returns:
        dict with SQL expressions for:
        - orders_qty: Заказы = В обработке + Выкупы + Возвраты (same as KPI ordersCount)
        - buyouts_qty: SUM(qty) WHERE status='завершен' (same as KPI completedCount)
        - returns_qty: SUM(returns_qty) — колонка Возвраты из sells_report (same as KPI returnsCount)
        - revenue_sum: SUM(revenue_sum) WHERE status='завершен' OR status='в обработке' (same as KPI revenue)
        - commission_sum: SUM(commission_sum) WHERE status='завершен' (same as KPI uzumCommission)
          Комиссия UZUM = файл sells_report из колонки Комиссия маркетплейса (сумы) со статусом из колонки Статус «Завершен»
        - logistics_sum: SUM(logistics_sum) WHERE status='завершен' (same as KPI uzumLogistics)
          Логистика UZUM = файл sells_report из колонки Логистический сбор со статусом «Завершен»
        - cogs_sum: SUM(cogs_sum * qty) WHERE status='завершен' OR status='в обработке' (same as KPI productCostTotal/productCostCompleted)
          Себест. прод. тов. = файл sells_report (из колонки Себестоимость (сумы) * из колонки Количество) со статусом из колонки Статус «Завершен» и «В обработке»
    """
    conditions = get_status_conditions()
    alias = f"{table_alias}." if table_alias else ""
    
    return {
        'orders_qty': f"( COALESCE(SUM(CASE WHEN ({conditions['processing']}) THEN {alias}qty ELSE 0 END), 0) + COALESCE(SUM(CASE WHEN ({conditions['completed']}) THEN {alias}qty ELSE 0 END), 0) + COALESCE(SUM(COALESCE({alias}returns_qty, 0)), 0) )",
        'buyouts_qty': f"COALESCE(SUM(CASE WHEN ({conditions['completed']}) THEN {alias}qty ELSE 0 END), 0)",
        'returns_qty': f"COALESCE(SUM(COALESCE({alias}returns_qty, 0)), 0)",
        'revenue_sum': f"COALESCE(SUM(CASE WHEN ({conditions['revenue']}) THEN {alias}revenue_sum ELSE 0 END), 0)",
        'commission_sum': f"COALESCE(SUM(CASE WHEN ({conditions['completed']}) THEN {alias}commission_sum ELSE 0 END), 0)",
        'logistics_sum': f"COALESCE(SUM(CASE WHEN ({conditions['completed']}) THEN {alias}logistics_sum ELSE 0 END), 0)",
        'cogs_sum': f"COALESCE(SUM(CASE WHEN ({conditions['revenue']}) THEN {alias}cogs_sum * {alias}qty ELSE 0 END), 0)",
    }


def get_profit_sql(revenue_expr: str, commission_expr: str, logistics_expr: str, cogs_expr: str) -> str:
    """
    Generate SQL expression for profit calculation (same formula as KPI).
    
    Formula: revenue - total_expenses
    where total_expenses = commission + logistics + cogs + taxes_1pct + extra_expenses
    - taxes_1pct = revenue * 0.01
    - extra_expenses = 0.0 (reserved for future)
    
    Args:
        revenue_expr: SQL expression for revenue (e.g., "s.revenue_sum")
        commission_expr: SQL expression for commission (e.g., "s.commission_sum")
        logistics_expr: SQL expression for logistics (e.g., "s.logistics_sum")
        cogs_expr: SQL expression for cogs (e.g., "s.cogs_sum")
    
    Returns:
        SQL expression for profit_sum
    """
    return f"""COALESCE({revenue_expr}, 0) - 
                COALESCE({commission_expr}, 0) - 
                COALESCE({logistics_expr}, 0) - 
                COALESCE({cogs_expr}, 0) - 
                (COALESCE({revenue_expr}, 0) * 0.01) - 
                0.0"""


def get_avg_check_sql(revenue_expr: str, orders_expr: str) -> str:
    """
    Generate SQL expression for average check calculation.
    
    Formula: revenue / NULLIF(orders_qty, 0) (if orders_qty > 0)
    Rounded to integer (no kopecks).
    
    Note: Uses orders_qty (all orders) for period-level calculation,
    not buyouts_qty (completed orders only).
    
    Args:
        revenue_expr: SQL expression for revenue (e.g., "s.revenue_sum")
        orders_expr: SQL expression for orders quantity (e.g., "s.orders_qty")
    
    Returns:
        SQL expression for avg_check
    """
    return f"""CASE 
                    WHEN COALESCE({orders_expr}, 0) > 0 
                    THEN ROUND(COALESCE({revenue_expr}, 0) / NULLIF({orders_expr}, 0))
                    ELSE 0
                END"""
