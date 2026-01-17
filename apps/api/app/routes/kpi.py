from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta
import logging
from app.db import get_db, qname
from app.deps import require_user
from app.utils.statuses import get_status_sql_condition
from fastapi import Depends

logger = logging.getLogger(__name__)
router = APIRouter()


def normalize_period(period: str) -> str:
    """Normalize period string to standard format: 7d, 30d, 90d, or all."""
    period_lower = period.lower().strip()
    
    if period_lower in ("7d", "week", "неделя"):
        return "7d"
    elif period_lower in ("30d", "30"):
        return "30d"
    elif period_lower in ("90d", "90"):
        return "90d"
    elif period_lower in ("all", "все", "все данные"):
        return "all"
    else:
        # Default to 30d if unknown
        return "30d"


def get_data_end_date(db: Session, user_id: UUID) -> datetime.date:
    """
    Get the maximum date from all data tables for the user.
    Returns the latest date from fact_sales, fact_storage_snapshot, fact_leftout_snapshot.
    If all are empty, returns CURRENT_DATE.
    shop_id is NOT considered (period is stable across shops).
    """
    data_end_query = text(f"""
        SELECT GREATEST(
            COALESCE((SELECT MAX(date_created)::date FROM {qname("fact_sales")} WHERE user_id = CAST(:user_id AS uuid)), DATE '1970-01-01'),
            COALESCE((SELECT MAX(loaded_at)::date FROM {qname("fact_storage_snapshot")} WHERE user_id = CAST(:user_id AS uuid)), DATE '1970-01-01'),
            COALESCE((SELECT MAX(loaded_at)::date FROM {qname("fact_leftout_snapshot")} WHERE user_id = CAST(:user_id AS uuid)), DATE '1970-01-01')
        ) AS data_end_date
    """)
    
    result = db.execute(data_end_query, {"user_id": str(user_id)})
    data_end_date = result.scalar()
    
    # If all tables are empty (all return 1970-01-01), use CURRENT_DATE
    if data_end_date and data_end_date.year == 1970:
        data_end_date = datetime.now().date()
    
    return data_end_date or datetime.now().date()


def period_range(period_code: str, data_end_date: datetime.date) -> dict:
    """
    Calculate date range for period code based on data_end_date.
    Returns: {code, date_from, date_to}
    - date_to = data_end_date (not CURRENT_DATE)
    - 7d: date_from = date_to - 6 days
    - 30d: date_from = date_to - 29 days
    - 90d: date_from = date_to - 89 days
    - all: date_from = None
    """
    date_to_iso = data_end_date.isoformat()
    
    if period_code == "all":
        date_from = None
    elif period_code == "7d":
        date_from = data_end_date - timedelta(days=6)
    elif period_code == "30d":
        date_from = data_end_date - timedelta(days=29)
    elif period_code == "90d":
        date_from = data_end_date - timedelta(days=89)
    else:
        # Fallback to 30d
        date_from = data_end_date - timedelta(days=29)
    
    return {
        "code": period_code,
        "date_from": date_from.isoformat() if date_from else None,
        "date_to": date_to_iso
    }


@router.get("/kpi/summary")
def kpi_summary(
    request: Request,
    period: str = "30d",
    shop_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    user_id = require_user(request)
    
    # Normalize period
    period_code = normalize_period(period)
    
    # Get data_end_date (maximum date from all data tables)
    data_end_date = get_data_end_date(db, user_id)
    
    # Calculate period range based on data_end_date
    period_range_dict = period_range(period_code, data_end_date)
    date_to_iso = period_range_dict["date_to"]
    
    # Protection: if date_to is None, use today
    if date_to_iso is None:
        date_to_date = datetime.now().date()
        date_to_iso = date_to_date.isoformat()
    else:
        date_to_date = datetime.fromisoformat(date_to_iso).date()
    
    date_from_iso = period_range_dict["date_from"]
    date_from = datetime.fromisoformat(date_from_iso).date() if date_from_iso else None
    
    # Validate shop_id if provided
    if shop_id:
        try:
            UUID(shop_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid shop_id format (must be UUID)"
            )
    
    logger.info(f"kpi_summary: user_id={user_id}, shop_id={shop_id}, period={period_code}, period_range={period_range_dict}")
    
    try:
        # Base parameters - ALWAYS includes user_id and date_to
        params_base = {
            "user_id": str(user_id),
            "date_to": date_to_iso,
            "shop_id": shop_id,  # Can be None
        }
        
        # Build base WHERE conditions for sales (filtered by periodRange)
        sales_where = ["user_id = CAST(:user_id AS uuid)"]
        if shop_id:
            sales_where.append("shop_id = CAST(:shop_id AS uuid)")
        if date_from:
            sales_where.append("date_created >= CAST(:date_from AS date)")
        sales_where.append("date_created < CAST(:date_to AS date) + INTERVAL '1 day'")
        
        sales_where_clause = " AND ".join(sales_where)
        
        # Prepare params for sales query
        sales_params = {**params_base}
        if date_from:
            sales_params["date_from"] = date_from.isoformat()
        
        # A) SALES aggregation
        # Get status conditions
        orders_condition = get_status_sql_condition('orders')  # All except cancelled
        processing_condition = get_status_sql_condition('processing')
        completed_condition = get_status_sql_condition('completed')
        
        sales_query = text(f"""
            SELECT 
                -- ordersCount/ordersValue: все кроме cancelled
                COALESCE(SUM(CASE WHEN {orders_condition} THEN qty ELSE 0 END), 0) as orders_count,
                COALESCE(SUM(CASE WHEN {orders_condition} THEN revenue_sum ELSE 0 END), 0) as orders_value,
                -- processingCount/processingValue: processing
                COALESCE(SUM(CASE WHEN {processing_condition} THEN qty ELSE 0 END), 0) as processing_count,
                COALESCE(SUM(CASE WHEN {processing_condition} THEN revenue_sum ELSE 0 END), 0) as processing_value,
                -- completedCount/completedValue: completed
                COALESCE(SUM(CASE WHEN {completed_condition} THEN qty ELSE 0 END), 0) as completed_count,
                COALESCE(SUM(CASE WHEN {completed_condition} THEN revenue_sum ELSE 0 END), 0) as completed_value,
                -- returns (from all orders)
                COALESCE(SUM(CASE WHEN {orders_condition} THEN returns_qty ELSE 0 END), 0) as returns_count,
                COALESCE(SUM(
                    CASE 
                        WHEN {orders_condition} AND qty > 0 
                        THEN (COALESCE(returns_qty, 0)::numeric) * (COALESCE(revenue_sum, 0) / NULLIF(qty, 0))
                        ELSE 0
                    END
                ), 0) as returns_value,
                -- uzumCommission/uzumLogistics: только completed
                COALESCE(SUM(CASE WHEN {completed_condition} THEN commission_sum ELSE 0 END), 0) as uzum_commission,
                COALESCE(SUM(CASE WHEN {completed_condition} THEN logistics_sum ELSE 0 END), 0) as uzum_logistics,
                -- productCost: completed OR processing
                COALESCE(SUM(
                    CASE 
                        WHEN {completed_condition} OR {processing_condition}
                        THEN cogs_sum 
                        ELSE 0 
                    END
                ), 0) as product_cost
            FROM {qname("fact_sales")}
            WHERE {sales_where_clause}
        """)
        
        sales_result = db.execute(sales_query, sales_params)
        sales_row = sales_result.fetchone()
        
        orders_count = float(sales_row[0] or 0)
        orders_value = float(sales_row[1] or 0)
        processing_count = float(sales_row[2] or 0)
        processing_value = float(sales_row[3] or 0)
        completed_count = float(sales_row[4] or 0)
        completed_value = float(sales_row[5] or 0)
        returns_count = float(sales_row[6] or 0)
        returns_value = float(sales_row[7] or 0)
        uzum_commission = float(sales_row[8] or 0)
        uzum_logistics = float(sales_row[9] or 0)
        product_cost = float(sales_row[10] or 0)
        
        # Derived metrics from sales
        return_rate = (returns_count / orders_count * 100) if orders_count > 0 else 0.0
        average_check = (completed_value / completed_count) if completed_count > 0 else 0.0
        revenue = completed_value
        
        # B) EXPENSES aggregation (filtered by periodRange)
        expenses_where = ["user_id = CAST(:user_id AS uuid)"]
        if date_from:
            expenses_where.append("date_written_off >= CAST(:date_from AS date)")
        expenses_where.append("date_written_off < CAST(:date_to AS date) + INTERVAL '1 day'")
        
        expenses_where_clause = " AND ".join(expenses_where)
        
        # Prepare params for expenses query
        expenses_params = {**params_base}
        if date_from:
            expenses_params["date_from"] = date_from.isoformat()
        
        expenses_query = text(f"""
            SELECT 
                COALESCE(SUM(
                    CASE 
                        WHEN source ILIKE '%реклам%' OR service ILIKE '%реклам%' OR operation_type ILIKE '%реклам%'
                        THEN cost_sum
                        ELSE 0
                    END
                ), 0) as uzum_ads,
                COALESCE(SUM(
                    CASE 
                        WHEN service ILIKE '%штраф%' OR operation_type ILIKE '%штраф%'
                        THEN amount_sum
                        ELSE 0
                    END
                ), 0) as uzum_fines
            FROM {qname("fact_expenses")}
            WHERE {expenses_where_clause}
        """)
        
        expenses_result = db.execute(expenses_query, expenses_params)
        expenses_row = expenses_result.fetchone()
        
        uzum_ads = float(expenses_row[0] or 0)
        uzum_fines = float(expenses_row[1] or 0)
        
        # C) Total expenses, profit, ratios
        total_expenses = uzum_commission + uzum_logistics + uzum_ads + uzum_fines + product_cost
        profit = revenue - total_expenses
        sales_profitability = (revenue / product_cost * 100) if product_cost > 0 else 0.0
        roi = ((revenue - product_cost) / product_cost * 100) if product_cost > 0 else 0.0
        
        # D) Revenue trend (compare with previous period)
        revenue_trend = 0.0
        if period_code != "all" and date_from:
            # Calculate previous period range
            days_diff = (date_to_date - date_from).days
            prev_date_from = date_from - timedelta(days=days_diff)
            prev_date_to = date_from
            
            prev_params = {
                "user_id": str(user_id),
                "prev_date_from": prev_date_from.isoformat(),
                "prev_date_to": prev_date_to.isoformat(),
            }
            
            if shop_id:
                prev_params["shop_id"] = shop_id
            
            prev_where = ["user_id = CAST(:user_id AS uuid)"]
            prev_where.append("date_created >= CAST(:prev_date_from AS date)")
            prev_where.append("date_created < CAST(:prev_date_to AS date) + INTERVAL '1 day'")
            if shop_id:
                prev_where.append("shop_id = CAST(:shop_id AS uuid)")
            
            prev_where_clause = " AND ".join(prev_where)
            
            prev_revenue_query = text(f"""
                SELECT COALESCE(SUM(CASE WHEN ({completed_condition}) THEN revenue_sum ELSE 0 END), 0)
                FROM {qname("fact_sales")}
                WHERE {prev_where_clause}
            """)
            
            prev_revenue_result = db.execute(prev_revenue_query, prev_params)
            prev_revenue = float(prev_revenue_result.scalar() or 0)
            
            if prev_revenue > 0:
                revenue_trend = ((revenue - prev_revenue) / prev_revenue * 100)
        
        # E) Cumulative revenue (YTD - Year To Date, from start of year relative to date_to)
        # Does NOT depend on period, only on date_to (data_end_date)
        # year_start = date_trunc('year', date_to::timestamp)::date
        year_start = datetime(date_to_date.year, 1, 1).date()
        year_start_iso = year_start.isoformat()
        
        cumulative_where = [
            "user_id = CAST(:user_id AS uuid)",
            f"({completed_condition})",
            "date_created >= CAST(:year_start AS date)",
            "date_created < CAST(:date_to AS date) + INTERVAL '1 day'"
        ]
        
        if shop_id:
            cumulative_where.append("shop_id = CAST(:shop_id AS uuid)")
        
        cumulative_where_clause = " AND ".join(cumulative_where)
        
        # Prepare params for cumulative query - MUST include date_to
        cumulative_params = {**params_base, "year_start": year_start_iso}
        
        cumulative_query = text(f"""
            SELECT COALESCE(SUM(revenue_sum), 0)
            FROM {qname("fact_sales")}
            WHERE {cumulative_where_clause}
        """)
        
        cumulative_result = db.execute(cumulative_query, cumulative_params)
        cumulative_revenue = float(cumulative_result.scalar() or 0)
        
        logger.info(f"cumulativeRevenue: year={date_to_date.year}, year_start={year_start_iso}, date_to={date_to_iso}, value={cumulative_revenue}")
        
        # F) STOCK aggregation
        stock_where = ["user_id = CAST(:user_id AS uuid)"]
        if shop_id:
            stock_where.append("shop_id = CAST(:shop_id AS uuid)")
        
        stock_where_clause = " AND ".join(stock_where)
        
        # Get latest snapshot
        max_loaded_query = text(f"""
            SELECT MAX(loaded_at)
            FROM {qname("fact_storage_snapshot")}
            WHERE {stock_where_clause}
        """)
        
        max_loaded_result = db.execute(max_loaded_query, params_base)
        max_loaded = max_loaded_result.scalar()
        
        stock_quantity = 0.0
        stock_cost = 0.0
        stock_retail_price = 0.0
        
        if max_loaded:
            # Get price and COGS units per SKU (last 90 days)
            price_cogs_where = [
                "user_id = CAST(:user_id AS uuid)",
                f"({completed_condition})",
                "date_created >= CAST(:price_date_from AS date)"
            ]
            
            if shop_id:
                price_cogs_where.append("shop_id = CAST(:shop_id AS uuid)")
            
            price_cogs_where_clause = " AND ".join(price_cogs_where)
            price_date_from = date_to_date - timedelta(days=90)
            
            # Prepare params for price_cogs query
            price_cogs_params = {**params_base, "price_date_from": price_date_from.isoformat()}
            
            price_cogs_query = text(f"""
                SELECT 
                    sku,
                    COALESCE(SUM(revenue_sum) / NULLIF(SUM(qty), 0), 0) as price_unit,
                    COALESCE(SUM(cogs_sum) / NULLIF(SUM(qty), 0), 0) as cogs_unit
                FROM {qname("fact_sales")}
                WHERE {price_cogs_where_clause}
                GROUP BY sku
            """)
            
            price_cogs_result = db.execute(price_cogs_query, price_cogs_params)
            price_cogs_map = {
                row[0]: (float(row[1] or 0), float(row[2] or 0))
                for row in price_cogs_result.fetchall()
            }
            
            # Get stock snapshot data
            snapshot_where = stock_where + ["loaded_at = :max_loaded"]
            snapshot_where_clause = " AND ".join(snapshot_where)
            
            # Prepare params for snapshot query
            snapshot_params = {**params_base, "max_loaded": max_loaded}
            
            snapshot_query = text(f"""
                SELECT 
                    sku,
                    COALESCE(fbo_stock_total, 0) as stock_qty
                FROM {qname("fact_storage_snapshot")}
                WHERE {snapshot_where_clause}
            """)
            
            snapshot_result = db.execute(snapshot_query, snapshot_params)
            
            for row in snapshot_result.fetchall():
                sku = row[0]
                stock_qty = float(row[1] or 0)
                price_unit, cogs_unit = price_cogs_map.get(sku, (0.0, 0.0))
                
                stock_quantity += stock_qty
                stock_cost += stock_qty * cogs_unit
                stock_retail_price += stock_qty * price_unit
        
        # B) Lost revenue: потенциальная выручка от товаров без остатков
        # Формула: (avg_daily_sales * 15) * price (для товаров где stock=0 и avg_daily_sales>0)
        # Prepare params for lost revenue query
        lost_revenue_params = {**params_base}
        
        # Calculate days_in_period: для all использовать 90 дней, иначе (date_to - date_from + 1)
        if date_from is None:
            # period=all: для расчета avg использовать date_from = date_to - 89 days
            date_from_for_avg = date_to_date - timedelta(days=89)
            days_in_period = 90
        else:
            date_from_for_avg = date_from
            days_in_period = (date_to_date - date_from).days + 1
        
        lost_revenue_params["date_from_for_avg"] = date_from_for_avg.isoformat()
        lost_revenue_params["days_in_period"] = days_in_period
        
        # Price window fallback: последние 90 дней до date_to
        price_window_from_date = date_to_date - timedelta(days=89)
        price_window_from = price_window_from_date.isoformat()
        price_window_to = date_to_iso
        lost_revenue_params["price_window_from"] = price_window_from
        
        # A) Определить snap_loaded_at (самый свежий snapshot до date_to, НЕ ограничивать >= date_from)
        snap_loaded_at_query = text(f"""
            SELECT MAX(loaded_at) AS snap_loaded_at
            FROM {qname("fact_storage_snapshot")}
            WHERE user_id = CAST(:user_id AS uuid)
                AND (:shop_id IS NULL OR shop_id = CAST(:shop_id AS uuid))
                AND loaded_at < CAST(:date_to AS date) + INTERVAL '1 day'
        """)
        
        snap_loaded_at_result = db.execute(snap_loaded_at_query, lost_revenue_params)
        snap_loaded_at = snap_loaded_at_result.scalar()
        
        # Если нет снапшота => lostRevenue = 0
        if snap_loaded_at is None:
            lost_revenue = 0.0
            rows_snapshot = 0
            rows_zero_stock = 0
            rows_with_sales = 0
            rows_with_price = 0
            rows_no_price = 0
            logger.info(f"lostRevenue: no snapshot, period={period_code}, date_from={date_from_iso or 'NULL'}, date_to={date_to_iso}, shop_id={shop_id}")
        else:
            lost_revenue_params["snap_loaded_at"] = snap_loaded_at
            
            # B) Расчет lostRevenue с avg_daily_sales из периода и ценами
            # Используем orders_condition (NOT cancelled) вместо completed для avg и цены
            lost_revenue_query = text(f"""
                WITH period_sales AS (
                    -- Продажи в периоде для расчета avg_daily_sales и цены (НЕ отменённые)
                    SELECT
                        NULLIF(TRIM(sku), '') AS sku,
                        NULLIF(TRIM(barcode), '') AS barcode,
                        SUM(qty) AS qty_period,
                        SUM(revenue_sum) AS rev_period
                    FROM {qname("fact_sales")}
                    WHERE user_id = CAST(:user_id AS uuid)
                        AND ({orders_condition})
                        AND (:shop_id IS NULL OR shop_id = CAST(:shop_id AS uuid))
                        AND date_created >= CAST(:date_from_for_avg AS date)
                        AND date_created < CAST(:date_to AS date) + INTERVAL '1 day'
                    GROUP BY NULLIF(TRIM(sku), ''), NULLIF(TRIM(barcode), '')
                ),
                price_fallback AS (
                    -- Fallback цены из окна 90 дней (НЕ отменённые)
                    SELECT
                        NULLIF(TRIM(sku), '') AS sku,
                        NULLIF(TRIM(barcode), '') AS barcode,
                        SUM(revenue_sum) AS rev_fallback,
                        SUM(qty) AS qty_fallback
                    FROM {qname("fact_sales")}
                    WHERE user_id = CAST(:user_id AS uuid)
                        AND ({orders_condition})
                        AND (:shop_id IS NULL OR shop_id = CAST(:shop_id AS uuid))
                        AND date_created >= CAST(:price_window_from AS date)
                        AND date_created < CAST(:date_to AS date) + INTERVAL '1 day'
                    GROUP BY NULLIF(TRIM(sku), ''), NULLIF(TRIM(barcode), '')
                ),
                snap AS (
                    -- Текущий snapshot склада
                    SELECT
                        NULLIF(TRIM(sku), '') AS sku,
                        NULLIF(TRIM(barcode), '') AS barcode,
                        COALESCE(fbo_stock_total, 0) AS stock_qty
                    FROM {qname("fact_storage_snapshot")}
                    WHERE user_id = CAST(:user_id AS uuid)
                        AND (:shop_id IS NULL OR shop_id = CAST(:shop_id AS uuid))
                        AND loaded_at = CAST(:snap_loaded_at AS timestamp)
                )
                SELECT
                    COUNT(*) AS rows_snapshot,
                    SUM(CASE WHEN p.stock_qty = 0 THEN 1 ELSE 0 END) AS rows_zero_stock,
                    SUM(CASE WHEN p.stock_qty = 0 AND COALESCE(p.qty_period, 0) > 0 THEN 1 ELSE 0 END) AS rows_with_sales,
                    SUM(CASE WHEN p.stock_qty = 0 AND COALESCE(p.qty_period, 0) > 0 AND p.final_price IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_price,
                    SUM(CASE WHEN p.stock_qty = 0 AND COALESCE(p.qty_period, 0) > 0 AND p.final_price IS NULL THEN 1 ELSE 0 END) AS rows_no_price,
                    COALESCE(SUM(
                        CASE
                            WHEN p.stock_qty = 0 
                                AND COALESCE(p.qty_period, 0) > 0 
                                AND p.final_price IS NOT NULL
                            THEN ((p.qty_period::numeric / CAST(:days_in_period AS numeric)) * 15 * p.final_price)
                            ELSE 0
                        END
                    ), 0) AS lost_revenue
                FROM (
                    SELECT 
                        s.sku,
                        s.barcode,
                        s.stock_qty,
                        ps.qty_period,
                        COALESCE(
                            -- Цена из периода
                            CASE WHEN ps.qty_period > 0 THEN ps.rev_period / ps.qty_period END,
                            -- Fallback цена из окна 90 дней
                            CASE WHEN pf.qty_fallback > 0 THEN pf.rev_fallback / pf.qty_fallback END
                        ) AS final_price
                    FROM snap s
                    LEFT JOIN period_sales ps ON (
                        (ps.sku = s.sku AND s.sku IS NOT NULL AND ps.sku IS NOT NULL)
                        OR (ps.barcode = s.barcode AND s.barcode IS NOT NULL AND ps.barcode IS NOT NULL)
                    )
                    LEFT JOIN price_fallback pf ON (
                        (pf.sku = s.sku AND s.sku IS NOT NULL AND pf.sku IS NOT NULL)
                        OR (pf.barcode = s.barcode AND s.barcode IS NOT NULL AND pf.barcode IS NOT NULL)
                    )
                ) p
            """)
            
            lost_revenue_result = db.execute(lost_revenue_query, lost_revenue_params)
            lost_revenue_row = lost_revenue_result.fetchone()
            
            if lost_revenue_row:
                rows_snapshot = int(lost_revenue_row[0] or 0)
                rows_zero_stock = int(lost_revenue_row[1] or 0)
                rows_with_sales = int(lost_revenue_row[2] or 0)
                rows_with_price = int(lost_revenue_row[3] or 0)
                rows_no_price = int(lost_revenue_row[4] or 0)
                lost_revenue = float(lost_revenue_row[5] or 0)
            else:
                rows_snapshot = 0
                rows_zero_stock = 0
                rows_with_sales = 0
                rows_with_price = 0
                rows_no_price = 0
                lost_revenue = 0.0
            
            logger.info(f"lostRevenue: value={lost_revenue}, days_in_period={days_in_period}, rows_snapshot={rows_snapshot}, rows_zero_stock={rows_zero_stock}, rows_with_sales={rows_with_sales}, rows_with_price={rows_with_price}, rows_no_price={rows_no_price}, snap_loaded_at={snap_loaded_at}, period={period_code}, date_from={date_from_iso or 'NULL'}, date_to={date_to_iso}, shop_id={shop_id}")
        
        # Для совместимости оставляем старые поля (можно удалить позже)
        lost_revenue_end = lost_revenue
        lost_revenue_peak = lost_revenue
        lost_revenue_delta = lost_revenue
        
        return {
            "cumulativeRevenue": cumulative_revenue,
            "ordersCount": orders_count,
            "ordersValue": orders_value,
            "processingCount": processing_count,
            "processingValue": processing_value,
            "completedCount": completed_count,
            "completedValue": completed_value,
            "returnsCount": returns_count,
            "returnsValue": returns_value,
            "returnRate": return_rate,
            "averageCheck": average_check,
            "revenue": revenue,
            "totalExpenses": total_expenses,
            "profit": profit,
            "salesProfitability": sales_profitability,
            "roi": roi,
            "revenueTrend": revenue_trend,
            "lostRevenue": lost_revenue,
            "lostRevenueEnd": lost_revenue_end,
            "lostRevenuePeak": lost_revenue_peak,
            "lostRevenueDelta": lost_revenue_delta,
            "lostRevenueDebug": {
                "snap_loaded_at": snap_loaded_at.isoformat() if snap_loaded_at and hasattr(snap_loaded_at, 'isoformat') else (str(snap_loaded_at) if snap_loaded_at else None),
                "days_in_period": days_in_period,
                "rows_snapshot": rows_snapshot,
                "rows_zero_stock": rows_zero_stock,
                "rows_with_sales": rows_with_sales,
                "rows_with_price": rows_with_price,
                "rows_no_price": rows_no_price
            },
            "uzumCommission": uzum_commission,
            "uzumLogistics": uzum_logistics,
            "uzumAds": uzum_ads,
            "uzumFines": uzum_fines,
            "productCost": product_cost,
            "stockQuantity": stock_quantity,
            "stockCost": stock_cost,
            "stockRetailPrice": stock_retail_price,
            "period_range": period_range_dict
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in kpi_summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
