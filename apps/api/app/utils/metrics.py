"""
Common metrics calculation utilities.
Shared between KPI and Charts endpoints to ensure consistency.
"""
from typing import Dict

from app.db import qname


def sql_net_qty(alias: str = "fs") -> str:
    """Чистое количество по строке: Количество − Возвраты (sells_report), не ниже 0."""
    alias = (alias or "fs").strip()
    p = f"{alias}."
    return f"GREATEST(COALESCE({p}qty, 0) - COALESCE({p}returns_qty, 0), 0)"


def sql_sales_barcode_norm(alias: str = "fs") -> str:
    """Нормализованный штрихкод из fact_sales (без хвоста .0)."""
    alias = (alias or "fs").strip()
    p = f"{alias}."
    stored = f"COALESCE({p}barcode_norm, '')"
    return (
        f"CASE WHEN RIGHT({stored}, 2) = '.0' "
        f"THEN LEFT({stored}, LENGTH({stored}) - 2) "
        f"ELSE {stored} END"
    )


def sql_effective_unit_cogs(alias: str = "fs") -> str:
    """
    Единичная себестоимость по строке продажи:
    ручная Profiboard (manual_product_cogs_history, effective_from <= дата продажи)
    или cogs_sum из загруженного sells-report.

    alias обязателен: без префикса таблицы PostgreSQL путает barcode_norm/user_id
    во вложенном SELECT с колонками history.
    """
    alias = (alias or "fs").strip()
    p = f"{alias}."
    bn = sql_sales_barcode_norm(alias)
    hist = qname("manual_product_cogs_history")
    return f"""COALESCE(
        (
            SELECT h.cogs_sum
            FROM {hist} h
            WHERE h.user_id = {p}user_id
              AND h.barcode_norm = {bn}
              AND {bn} <> ''
              AND h.effective_from <= ({p}date_created)::date
            ORDER BY h.effective_from DESC, h.created_at DESC
            LIMIT 1
        ),
        COALESCE({p}cogs_sum, 0)
    )"""


def sql_cogs_line_amount(alias: str = "fs") -> str:
    """Себестоимость по строке: unit COGS × (Количество − Возвраты)."""
    alias = (alias or "fs").strip()
    return f"{sql_effective_unit_cogs(alias)} * {sql_net_qty(alias)}"


def sql_leftout_barcode_norm(alias: str = "lo") -> str:
    """Нормализованный штрихкод из left-out-report_old snapshot."""
    alias = (alias or "lo").strip()
    p = f"{alias}."
    stored = (
        f"COALESCE(NULLIF(trim({p}barcode_norm), ''), "
        f"NULLIF(trim({p}barcode), ''))"
    )
    return (
        f"CASE WHEN RIGHT({stored}, 2) = '.0' "
        f"THEN LEFT({stored}, LENGTH({stored}) - 2) "
        f"ELSE {stored} END"
    )


def sql_effective_unit_cogs_as_of(alias: str, as_of_date_expr: str) -> str:
    """
    Единичная себестоимость для оценки остатков на дату:
    ручная Profiboard (effective_from <= as_of_date) или cost_sum из left-out-report_old.
    """
    alias = (alias or "lo").strip()
    p = f"{alias}."
    bn = sql_leftout_barcode_norm(alias)
    hist = qname("manual_product_cogs_history")
    return f"""COALESCE(
        (
            SELECT h.cogs_sum
            FROM {hist} h
            WHERE h.user_id = {p}user_id
              AND h.barcode_norm = {bn}
              AND {bn} <> ''
              AND h.effective_from <= ({as_of_date_expr})::date
            ORDER BY h.effective_from DESC, h.created_at DESC
            LIMIT 1
        ),
        COALESCE({p}cost_sum, 0)
    )"""


def sql_latest_profiboard_unit_cogs(alias: str = "lo") -> str:
    """
    Последняя ручная себестоимость Profiboard по штрихкоду (max effective_from).
    Для текущего склада FBO — как actual_cogs на вкладке «Себестоимость».
    Fallback: cost_sum из left-out-report_old.
    """
    alias = (alias or "lo").strip()
    p = f"{alias}."
    bn = sql_leftout_barcode_norm(alias)
    hist = qname("manual_product_cogs_history")
    manual = qname("manual_product_cogs")
    return f"""COALESCE(
        (
            SELECT cogs_sum FROM (
                SELECT h.cogs_sum, h.effective_from, h.created_at
                FROM {hist} h
                WHERE h.user_id = {p}user_id
                  AND h.barcode_norm = {bn}
                  AND {bn} <> ''
                UNION ALL
                SELECT m.cogs_sum, m.effective_from, m.updated_at AS created_at
                FROM {manual} m
                WHERE m.user_id = {p}user_id
                  AND m.barcode_norm = {bn}
                  AND {bn} <> ''
                  AND m.effective_from IS NOT NULL
            ) pb
            ORDER BY pb.effective_from DESC, pb.created_at DESC
            LIMIT 1
        ),
        COALESCE({p}cost_sum, 0)
    )"""


def sql_stock_cogs_line_amount(alias: str = "lo") -> str:
    """Себестоимость строки склада FBO: последняя Profiboard × «В продаже»."""
    alias = (alias or "lo").strip()
    p = f"{alias}."
    qty = f"GREATEST(COALESCE({p}in_sale_qty, 0), 0)"
    return f"{sql_latest_profiboard_unit_cogs(alias)} * {qty}"


def sql_fbs_stock_cogs_line_amount(alias: str = "lo") -> str:
    """Себестоимость строки склада FBS: последняя Profiboard × «Остаток FBS»."""
    alias = (alias or "lo").strip()
    p = f"{alias}."
    qty = f"GREATEST(COALESCE({p}fbs_qty, 0), 0)"
    return f"{sql_latest_profiboard_unit_cogs(alias)} * {qty}"


def sql_unit_price_from_rows(revenue_col: str, qty_col: str, returns_col: str) -> str:
    """Цена: SUM(Выручка) / SUM(Количество − Возвраты)."""
    net = f"GREATEST(COALESCE({qty_col}, 0) - COALESCE({returns_col}, 0), 0)"
    return f"""CASE WHEN COALESCE(SUM({net}), 0) > 0
                     THEN SUM(COALESCE({revenue_col}, 0)) / NULLIF(SUM({net}), 0)
                     ELSE 0
                END"""


def get_status_conditions() -> Dict[str, str]:
    """
    Get SQL status conditions used in KPI calculations.
    Returns the same conditions for both KPI and Charts to ensure consistency.
    Поддерживаются RU и UZ значения (на случай данных, загруженных до маппинга значений).
    """
    # Выручка/выкупы: RU или UZ эквиваленты «завершен» и «в обработке»
    revenue_ru = "(lower(trim(status)) IN ('завершен', 'завершён') OR lower(trim(status)) = 'в обработке')"
    revenue_uz = " OR (lower(trim(status)) LIKE '%yetkazilgan%' OR lower(trim(status)) LIKE '%yakunlangan%' OR lower(trim(status)) LIKE '%yakunlandi%' OR lower(trim(status)) LIKE '%qayta ishlashda%' OR lower(trim(status)) LIKE '%qayta ishlanmoqda%' OR lower(trim(status)) LIKE '%jarayonda%')"
    return {
        'processing': "(lower(trim(status)) = 'в обработке' OR lower(trim(status)) LIKE '%qayta ishlashda%' OR lower(trim(status)) LIKE '%qayta ishlanmoqda%' OR lower(trim(status)) LIKE '%jarayonda%')",
        'completed': "(lower(trim(status)) IN ('завершен', 'завершён') OR lower(trim(status)) LIKE '%yetkazilgan%' OR lower(trim(status)) LIKE '%yakunlangan%' OR lower(trim(status)) LIKE '%yakunlandi%')",
        'cancelled': "(lower(trim(status)) IN ('отменен', 'отменён') OR lower(trim(status)) LIKE '%bekor qilindi%' OR lower(trim(status)) LIKE '%rad etildi%')",
        'revenue': "(" + revenue_ru + revenue_uz + ")",
    }


def get_kpi_sales_breakdown_sql(table_alias: str = "fs") -> Dict[str, str]:
    """
    SQL-выражения для разбивки продаж как на вкладке Сводка (KPI summary).
    Для использования в SELECT ... GROUP BY (например, по штрихкоду или товару).
    """
    conditions = get_status_conditions()
    p = f"{table_alias}." if table_alias else ""
    proc = conditions["processing"]
    comp = conditions["completed"]
    qty = f"COALESCE({p}qty, 0)"
    revenue = f"COALESCE({p}revenue_sum, 0)"
    returns = f"COALESCE({p}returns_qty, 0)"
    price = f"COALESCE({p}price_sum, 0)"
    return {
        "processing_qty": f"COALESCE(SUM(CASE WHEN {proc} THEN {qty} ELSE 0 END), 0)",
        "processing_value": f"COALESCE(SUM(CASE WHEN {proc} THEN {revenue} ELSE 0 END), 0)",
        "completed_qty": f"COALESCE(SUM(CASE WHEN {comp} THEN {qty} ELSE 0 END), 0)",
        "completed_value": f"COALESCE(SUM(CASE WHEN {comp} THEN {revenue} ELSE 0 END), 0)",
        "returns_value": f"COALESCE(SUM({returns} * {price}), 0)",
        "orders_qty": (
            f"(COALESCE(SUM(CASE WHEN {proc} THEN {qty} ELSE 0 END), 0)"
            f" + COALESCE(SUM(CASE WHEN {comp} THEN {qty} ELSE 0 END), 0)"
            f" + COALESCE(SUM({returns}), 0))"
        ),
        "orders_value": (
            f"(COALESCE(SUM(CASE WHEN {proc} THEN {revenue} ELSE 0 END), 0)"
            f" + COALESCE(SUM(CASE WHEN {comp} THEN {revenue} ELSE 0 END), 0)"
            f" + COALESCE(SUM({returns} * {price}), 0))"
        ),
    }


def get_sales_metrics_sql(
    table_alias: str = "fs",
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
        - commission_sum: SUM(commission_sum) WHERE status='завершен' OR status='в обработке' (same as KPI uzumCommission)
          Комиссия UZUM = файл sells_report из колонки Комиссия маркетплейса (сумы) со статусом из колонки Статус «Завершен» и «В обработке»
        - logistics_sum: SUM(logistics_sum) WHERE status='завершен' OR status='в обработке' (same as KPI uzumLogistics)
          Логистика UZUM = файл sells_report из колонки Логистический сбор со статусом «Завершен» и «В обработке»
        - cogs_sum: SUM(cogs_sum * (qty - returns_qty)) WHERE status='завершен' OR status='в обработке' (same as KPI productCostTotal/productCostCompleted)
          Себест. прод. тов. = файл sells_report (Себестоимость (сумы) × (Количество − Возвраты)) со статусом «Завершен» и «В обработке»
    """
    conditions = get_status_conditions()
    alias = f"{table_alias}." if table_alias else ""
    
    return {
        'orders_qty': f"( COALESCE(SUM(CASE WHEN ({conditions['processing']}) THEN {alias}qty ELSE 0 END), 0) + COALESCE(SUM(CASE WHEN ({conditions['completed']}) THEN {alias}qty ELSE 0 END), 0) + COALESCE(SUM(COALESCE({alias}returns_qty, 0)), 0) )",
        'buyouts_qty': f"COALESCE(SUM(CASE WHEN ({conditions['completed']}) THEN {alias}qty ELSE 0 END), 0)",
        'returns_qty': f"COALESCE(SUM(COALESCE({alias}returns_qty, 0)), 0)",
        'revenue_sum': f"COALESCE(SUM(CASE WHEN ({conditions['revenue']}) THEN {alias}revenue_sum ELSE 0 END), 0)",
        'commission_sum': f"COALESCE(SUM(CASE WHEN ({conditions['revenue']}) THEN {alias}commission_sum ELSE 0 END), 0)",
        'logistics_sum': f"COALESCE(SUM(CASE WHEN ({conditions['revenue']}) THEN {alias}logistics_sum ELSE 0 END), 0)",
        'cogs_sum': f"COALESCE(SUM(CASE WHEN ({conditions['revenue']}) THEN {sql_cogs_line_amount(table_alias)} ELSE 0 END), 0)",
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
