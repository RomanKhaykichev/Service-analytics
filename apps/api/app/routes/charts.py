from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta
import logging
import re
from app.db import get_db, qname
from app.deps import require_user
from app.routes.kpi import get_data_end_date, period_range, normalize_period
from app.utils.statuses import get_status_sql_condition
from app.utils.metrics import get_status_conditions, get_sales_metrics_sql, get_profit_sql, get_avg_check_sql
from app.utils.barcode import barcode_norm_sql
from app.utils.shop_filter import normalize_shop, shop_filter_condition, storage_barcode_filter_sql
from app.schemas import (
    RevenueDailyResponse,
    RevenuePoint,
    RevenueFilters,
    PeriodInfo,
    StockCurrentResponse,
    StockItem,
    StockFilters,
    ChartStockCurrentResponse,
    Filters,
    StockDailyResponse,
    StockDailyPoint,
    StockDailyFilters,
    UzumServicesDailyResponse,
    UzumServicesPoint,
    UzumServicesFilters,
    OrdersSalesDailyResponse,
    OrdersSalesDailyPoint,
    OrdersSalesDailyFilters,
    DailySummaryResponse,
    DailySummaryPoint,
    DailySummaryFilters,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/charts/revenue-daily", response_model=RevenueDailyResponse)
async def get_revenue_daily(
    user_id: UUID = Depends(require_user),
    period: str = Query(default="30d", description="Period: 7d, 30d, 90d, or all"),
    shop_id: Optional[str] = Query(default=None, description="Shop UUID (dim_shop)"),
    shop: Optional[str] = Query(default=None, description="Shop name (string) for seller-storage filtering by barcode"),
    db: Session = Depends(get_db)
):
    """Get daily revenue chart data from fact_sales with revenue, orders, and averageCheck.
    When shop (string) is set, filter by products present in fact_storage_snapshot for that shop (barcode_norm).
    """
    # Normalize period
    period_code = normalize_period(period)
    
    # Get data_end_date (maximum date from all data tables)
    data_end_date = get_data_end_date(db, user_id)
    
    # Calculate period range based on data_end_date (same logic as kpi.py)
    period_range_dict = period_range(period_code, data_end_date)
    
    date_to_iso = period_range_dict["date_to"]
    date_to_date = datetime.fromisoformat(date_to_iso).date()
    date_from_iso = period_range_dict["date_from"]
    date_from = datetime.fromisoformat(date_from_iso).date() if date_from_iso else None
    
    shop_norm = normalize_shop(shop)
    logger.info(f"get_revenue_daily: user_id={user_id}, period={period_code}, shop_id={shop_id}, shop={shop}, shop_norm={shop_norm}, period_range={period_range_dict}")
    
    # Validate shop_id if provided (only when shop is not used)
    if shop_id and not shop:
        try:
            UUID(shop_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid shop_id format (must be UUID). For seller-storage use 'shop' parameter."
            )
    
    try:
        # Get status conditions
        completed_condition = get_status_sql_condition('completed')
        orders_condition = get_status_sql_condition('orders')  # всё кроме отмен
        
        # Build parameters
        params = {
            "user_id": str(user_id),
            "date_to": date_to_iso
        }
        
        # Shop filter: единый helper (storage barcode или shop_id)
        shop_condition_frag, shop_params = shop_filter_condition(shop, shop_id, outer_table_alias="fact_sales")
        params.update(shop_params)
        shop_condition = f"AND {shop_condition_frag}" if shop_condition_frag else ""
        
        # Build date_from condition
        date_from_condition = ""
        if date_from:
            params["date_from"] = date_from.isoformat()
            date_from_condition = "AND date_created >= CAST(:date_from AS date)"
        
        # Build query - агрегируем по d = date_created::date
        # Use unqualified fact_sales in FROM so EXISTS correlation works (table is schema-qualified via qname in FROM)
        query = text(f"""
            SELECT 
                date_created::date AS day,
                COALESCE(SUM(CASE WHEN ({completed_condition}) THEN revenue_sum ELSE 0 END), 0) AS revenue,
                COALESCE(SUM(CASE WHEN ({orders_condition}) THEN qty ELSE 0 END), 0) AS orders,
                COALESCE(SUM(CASE WHEN ({completed_condition}) THEN qty ELSE 0 END), 0) AS completed_qty
            FROM {qname("fact_sales")} fact_sales
            WHERE fact_sales.user_id = CAST(:user_id AS uuid)
                {shop_condition}
                {date_from_condition}
                AND fact_sales.date_created < CAST(:date_to AS date) + INTERVAL '1 day'
            GROUP BY date_created::date
            ORDER BY day ASC
        """)
        
        result = db.execute(query, params)
        rows = result.fetchall()
        logger.info(f"get_revenue_daily: found {len(rows)} points, period_range={period_range_dict}")
        
        # Extract date, revenue, orders, averageCheck from rows
        points = []
        for row in rows:
            try:
                day = row[0]
                date_str = day.isoformat() if hasattr(day, 'isoformat') else str(day)
                revenue = float(row[1]) if row[1] is not None else 0.0
                orders = float(row[2]) if row[2] is not None else 0.0
                completed_qty = float(row[3]) if row[3] is not None else 0.0
                # averageCheck = revenue / completed_qty (как в KPI summary)
                average_check = (revenue / completed_qty) if completed_qty > 0 else 0.0
                points.append(RevenuePoint(
                    date=date_str,
                    revenue=revenue,
                    orders=orders,
                    averageCheck=average_check
                ))
            except (IndexError, ValueError, TypeError) as e:
                logger.warning(f"Error parsing row in revenue-daily: {e}, row: {row}")
                continue
        
        # Return period range from calculated values
        return RevenueDailyResponse(
            points=points,
            period=PeriodInfo(
                code=period_code,
                date_from=date_from_iso or "",
                date_to=date_to_iso
            ),
            filters=RevenueFilters(shop_id=shop_id, shop=shop)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_revenue_daily: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/charts/stock-current", response_model=StockCurrentResponse)
async def get_stock_current(
    user_id: UUID = Depends(require_user),
    shop_id: Optional[str] = Query(default=None, description="Shop UUID"),
    shop: Optional[str] = Query(default=None, description="Shop name (string) for seller-storage filtering by barcode"),
    q: Optional[str] = Query(default=None, description="Search in sku, product_name, barcode"),
    limit: int = Query(default=200, le=500, description="Max number of items to return"),
    db: Session = Depends(get_db)
):
    """Get current stock snapshot from v_product_current_stock. Filter by shop (seller-storage) via barcode set.
    Shop is string (shop_raw from fact_storage_snapshot); no CAST(shop AS uuid). View has no barcode_norm — use computed expr."""
    shop_norm = normalize_shop(shop)
    logger.info(f"get_stock_current: user_id={user_id}, shop_id={shop_id}, shop={shop!r}, shop_norm={shop_norm!r}, q={q}, limit={limit}")
    try:
        conditions = ["v.user_id = CAST(:user_id AS uuid)"]
        params = {"user_id": str(user_id), "limit": limit}
        # Shop filter: shop is string (seller-storage shop_raw). View v_product_current_stock has no barcode_norm — use computed only
        shop_cond, shop_params = shop_filter_condition(
            shop,
            shop_id,
            outer_table_alias="v",
            outer_barcode_norm_expr=barcode_norm_sql("v.barcode"),
        )
        params.update(shop_params)
        if shop_cond:
            conditions.append(shop_cond)
        if q:
            conditions.append("(v.sku ILIKE :q OR v.product_name ILIKE :q OR v.barcode ILIKE :q)")
            params["q"] = f"%{q}%"
        where_clause = " AND ".join(conditions)
        query = text(f"""
            SELECT 
                v.barcode,
                v.sku,
                v.product_name,
                v.stock_qty,
                v.coverage_days,
                v.turnover_days,
                v.fee_total_30d,
                v.storage_type,
                v.size_group
            FROM {qname("v_product_current_stock")} v
            WHERE {where_clause}
            ORDER BY v.stock_qty DESC NULLS LAST, v.fee_total_30d DESC NULLS LAST
            LIMIT :limit
        """)
        result = db.execute(query, params)
        rows = result.fetchall()
        logger.info(f"get_stock_current: shop_norm={shop_norm!r}, row_count={len(rows)}")
        items = []
        for row in rows:
            try:
                barcode = str(row[0]) if len(row) > 0 and row[0] else ""
                sku = str(row[1]) if len(row) > 1 and row[1] else ""
                product_name = str(row[2]) if len(row) > 2 and row[2] else None
                stock_qty = float(row[3]) if len(row) > 3 and row[3] is not None else None
                coverage_days = float(row[4]) if len(row) > 4 and row[4] is not None else None
                turnover_days = float(row[5]) if len(row) > 5 and row[5] is not None else None
                fee_total_30d = float(row[6]) if len(row) > 6 and row[6] is not None else None
                storage_type = str(row[7]) if len(row) > 7 and row[7] else None
                size_group = str(row[8]) if len(row) > 8 and row[8] else None
                items.append(StockItem(
                    barcode=barcode,
                    sku=sku,
                    product_name=product_name,
                    stock_qty=stock_qty,
                    coverage_days=coverage_days,
                    turnover_days=turnover_days,
                    fee_total_30d=fee_total_30d,
                    storage_type=storage_type,
                    size_group=size_group
                ))
            except (IndexError, ValueError, TypeError) as e:
                logger.warning(f"Error parsing row in stock-current: {e}, row: {row}")
                continue
        if not items:
            logger.warning("get_stock_current: no data for v_product_current_stock (returning empty list)")
            try:
                user_rows = db.execute(
                    text(f"SELECT COUNT(*) FROM {qname('fact_storage_snapshot')} WHERE user_id = CAST(:user_id AS uuid)"),
                    {"user_id": str(user_id)},
                ).scalar() or 0
                selected_snapshot = db.execute(
                    text(f"""
                        SELECT upload_batch_id, loaded_at
                        FROM (
                            SELECT user_id, upload_batch_id, loaded_at,
                                   ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY loaded_at DESC NULLS LAST) AS rn
                            FROM {qname('fact_storage_snapshot')}
                            WHERE user_id = CAST(:user_id AS uuid)
                        ) t WHERE rn = 1
                    """),
                    {"user_id": str(user_id)},
                ).fetchone()
                shop_rows = None
                if shop_norm:
                    shop_rows = db.execute(
                        text(f"""
                            SELECT COUNT(*) FROM {qname('fact_storage_snapshot')}
                            WHERE user_id = CAST(:user_id AS uuid)
                              AND upper(regexp_replace(trim(COALESCE(shop_raw, '')), '\\s+', ' ', 'g')) = :shop_norm
                        """),
                        {"user_id": str(user_id), "shop_norm": shop_norm},
                    ).scalar() or 0
                logger.info(
                    "get_stock_current: self-check when empty: user_rows_count=%s, shop_rows_count=%s, selected_snapshot=%s",
                    user_rows,
                    shop_rows,
                    (str(selected_snapshot[0]), str(selected_snapshot[1])) if selected_snapshot else None,
                )
            except Exception as diag_err:
                logger.warning("get_stock_current: self-check failed: %s", diag_err)
        return StockCurrentResponse(
            items=items,
            filters=StockFilters(shop_id=shop_id, shop=shop, q=q or "")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_stock_current: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/charts/stock-daily", response_model=StockDailyResponse)
async def get_stock_daily(
    user_id: UUID = Depends(require_user),
    period: str = Query(default="30d", description="Period: 7d, 30d, 90d, or all"),
    shop_id: Optional[str] = Query(default=None, description="Shop UUID"),
    db: Session = Depends(get_db)
):
    """Get daily stock chart data."""
    # Normalize period
    period_code = normalize_period(period)
    
    # Get data_end_date (maximum date from all data tables)
    data_end_date = get_data_end_date(db, user_id)
    
    # Calculate period range based on data_end_date
    period_range_dict = period_range(period_code, data_end_date)
    
    date_to_iso = period_range_dict["date_to"]
    date_to_date = datetime.fromisoformat(date_to_iso).date()
    date_from_iso = period_range_dict["date_from"]
    date_from = datetime.fromisoformat(date_from_iso).date() if date_from_iso else None
    
    # For period=all, if date_from is None, use MIN(loaded_at)::date or very early date
    if period_code == "all" and date_from is None:
        # Get minimum loaded_at date for user
        min_date_query = text(f"""
            SELECT MIN(loaded_at)::date
            FROM {qname("fact_leftout_snapshot")}
            WHERE user_id = CAST(:user_id AS uuid)
        """)
        min_date_result = db.execute(min_date_query, {"user_id": str(user_id)})
        min_date = min_date_result.scalar()
        if min_date:
            date_from = min_date
        else:
            # Fallback to 365 days before date_to
            date_from = date_to_date - timedelta(days=364)
        date_from_iso = date_from.isoformat()
    
    # Ensure date_from is set
    if not date_from:
        date_from = date_to_date - timedelta(days=29)  # Default to 30d
        date_from_iso = date_from.isoformat()
    
    # Normalize shop_id: empty string -> None
    if shop_id == "":
        shop_id = None
    
    logger.info(f"get_stock_daily: user_id={user_id}, period={period_code}, shop_id={shop_id}, date_from={date_from_iso}, date_to={date_to_iso}")
    
    # Validate shop_id if provided
    if shop_id:
        try:
            UUID(shop_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid shop_id format (must be UUID)"
            )
    
    try:
        # Get status condition for orders (all except cancelled)
        orders_condition = get_status_sql_condition('orders')
        
        # Build parameters - always include shop_id (can be None)
        params = {
            "user_id": str(user_id),
            "date_from": date_from_iso,
            "date_to": date_to_iso,
            "shop_id": shop_id  # Always include, can be None
        }
        
        # Build query: for each day, get MAX(loaded_at) in that day, then SUM(marketplace_side)
        # Also get orders from fact_sales (same logic as revenue-daily chart)
        query = text(f"""
            WITH date_series AS (
                SELECT generate_series(
                    CAST(:date_from AS date),
                    CAST(:date_to AS date),
                    INTERVAL '1 day'
                )::date AS day
            ),
            day_last AS (
                SELECT 
                    loaded_at::date AS d, 
                    MAX(loaded_at) AS last_loaded_at
                FROM {qname("fact_leftout_snapshot")}
                WHERE user_id = CAST(:user_id AS uuid)
                    AND (:shop_id IS NULL OR shop_id = CAST(:shop_id AS uuid))
                    AND loaded_at::date >= CAST(:date_from AS date)
                    AND loaded_at::date <= CAST(:date_to AS date)
                GROUP BY loaded_at::date
            ),
            day_sum_stock AS (
                SELECT 
                    dl.d AS date, 
                    COALESCE(SUM(COALESCE(f.marketplace_side, 0)), 0) AS stock
                FROM day_last dl
                JOIN {qname("fact_leftout_snapshot")} f
                    ON f.user_id = CAST(:user_id AS uuid)
                    AND (:shop_id IS NULL OR f.shop_id = CAST(:shop_id AS uuid))
                    AND f.loaded_at = dl.last_loaded_at
                GROUP BY dl.d
            ),
            sales_day AS (
                SELECT 
                    date_created::date AS d,
                    SUM(COALESCE(qty, 0)) AS orders
                FROM {qname("fact_sales")}
                WHERE user_id = CAST(:user_id AS uuid)
                    AND ({orders_condition})
                    AND (:shop_id IS NULL OR shop_id = CAST(:shop_id AS uuid))
                    AND date_created >= CAST(:date_from AS date)
                    AND date_created < CAST(:date_to AS date) + INTERVAL '1 day'
                GROUP BY date_created::date
            )
            SELECT 
                d.day::date AS date,
                COALESCE(s.orders, 0) AS orders,
                COALESCE(ds.stock, 0) AS stock
            FROM date_series d
            LEFT JOIN sales_day s ON s.d = d.day
            LEFT JOIN day_sum_stock ds ON ds.date = d.day
            ORDER BY d.day ASC
        """)
        
        result = db.execute(query, params)
        rows = result.fetchall()
        logger.info(f"get_stock_daily: found {len(rows)} points")
        
        # Extract points from rows
        points = []
        for row in rows:
            try:
                day = row[0]
                date_str = day.isoformat() if hasattr(day, 'isoformat') else str(day)
                orders = float(row[1]) if row[1] is not None else 0.0
                stock = float(row[2]) if row[2] is not None else 0.0
                points.append(StockDailyPoint(
                    date=date_str,
                    orders=orders,
                    stock=stock
                ))
            except (IndexError, ValueError, TypeError) as e:
                logger.warning(f"Error parsing row in stock-daily: {e}, row: {row}")
                continue
        
        # Return response
        return StockDailyResponse(
            points=points,
            period=PeriodInfo(
                code=period_code,
                date_from=date_from_iso or "",
                date_to=date_to_iso
            ),
            filters=StockDailyFilters(shop_id=shop_id)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_stock_daily: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/charts/uzum-services-daily", response_model=UzumServicesDailyResponse)
async def get_uzum_services_daily(
    user_id: UUID = Depends(require_user),
    period: str = Query(default="30d", description="Period: 7d, 30d, 90d, or all"),
    shop_id: Optional[str] = Query(default=None, description="Shop UUID"),
    shop: Optional[str] = Query(default=None, description="Shop name (string) for seller-storage filtering by barcode"),
    db: Session = Depends(get_db)
):
    """Get daily UZUM services chart data: storage, ads, fines from fact_expenses;
    commission, logistics from fact_sales (filterable by shop via barcode_norm)."""
    # Normalize period
    period_code = normalize_period(period)
    
    # Get data_end_date (maximum date from all data tables)
    data_end_date = get_data_end_date(db, user_id)
    
    # Calculate period range based on data_end_date
    period_range_dict = period_range(period_code, data_end_date)
    
    date_to_iso = period_range_dict["date_to"]
    date_to_date = datetime.fromisoformat(date_to_iso).date()
    date_from_iso = period_range_dict["date_from"]
    date_from = datetime.fromisoformat(date_from_iso).date() if date_from_iso else None
    
    shop_norm = normalize_shop(shop)
    
    # For period=all, if date_from is None, use MIN(date_written_off) or very early date
    if period_code == "all" and date_from is None:
        min_date_query = text(f"""
            SELECT MIN(date_written_off)::date
            FROM {qname("fact_expenses")}
            WHERE user_id = CAST(:user_id AS uuid)
        """)
        min_date_result = db.execute(min_date_query, {"user_id": str(user_id)})
        min_date = min_date_result.scalar()
        if min_date:
            date_from = min_date
        else:
            date_from = date_to_date - timedelta(days=364)
        date_from_iso = date_from.isoformat()
    
    # Ensure date_from is set
    if not date_from:
        date_from = date_to_date - timedelta(days=29)
        date_from_iso = date_from.isoformat()
    
    logger.info(f"get_uzum_services_daily: user_id={user_id}, period={period_code}, shop={shop}, shop_norm={shop_norm}, date_from={date_from_iso}, date_to={date_to_iso}")
    
    try:
        params_expenses = {
            "user_id": str(user_id),
            "date_from": date_from_iso,
            "date_to": date_to_iso
        }
        
        # 1) Expenses: storage, ads, fines (no barcode filter)
        query_expenses = text(f"""
            SELECT 
                date_written_off::date AS day,
                COALESCE(SUM(
                    CASE 
                        WHEN lower(trim(COALESCE(operation_type, ''))) = 'оплата' 
                        THEN COALESCE(cost_sum, 0)
                        WHEN lower(trim(COALESCE(operation_type, ''))) = 'возврат' 
                        THEN -COALESCE(cost_sum, 0)
                        ELSE 0
                    END
                ), 0) AS storage,
                COALESCE(SUM(
                    CASE 
                        WHEN (COALESCE(source, '') ILIKE '%маркетинг%' OR COALESCE(source, '') ILIKE '%marketing%')
                             AND (COALESCE(operation_type, '') ILIKE '%оплат%' OR COALESCE(operation_type, '') ILIKE '%payment%')
                        THEN COALESCE(cost_sum, 0)
                        ELSE 0
                    END
                ), 0) AS ads,
                COALESCE(SUM(
                    CASE 
                        WHEN COALESCE(service, '') ILIKE '%штраф%'
                        THEN COALESCE(amount_sum, 0)
                        ELSE 0
                    END
                ), 0) AS fines
            FROM {qname("fact_expenses")}
            WHERE user_id = CAST(:user_id AS uuid)
                AND date_written_off >= CAST(:date_from AS date)
                AND date_written_off < CAST(:date_to AS date) + INTERVAL '1 day'
            GROUP BY date_written_off::date
            ORDER BY day ASC
        """)
        
        result_expenses = db.execute(query_expenses, params_expenses)
        rows_expenses = result_expenses.fetchall()
        
        # 2) Sales: commission, logistics (filterable by shop via barcode_norm)
        completed_condition = get_status_sql_condition('completed')
        params_sales = {
            "user_id": str(user_id),
            "date_from": date_from_iso,
            "date_to": date_to_iso
        }
        shop_condition_sales_frag, shop_sales_params = shop_filter_condition(shop, shop_id, outer_table_alias="fact_sales")
        params_sales.update(shop_sales_params)
        shop_condition_sales = f"AND {shop_condition_sales_frag}" if shop_condition_sales_frag else ""
        
        query_sales = text(f"""
            SELECT 
                date_created::date AS day,
                COALESCE(SUM(commission_sum), 0) AS commission,
                COALESCE(SUM(logistics_sum), 0) AS logistics
            FROM {qname("fact_sales")} fact_sales
            WHERE fact_sales.user_id = CAST(:user_id AS uuid)
                AND ({completed_condition})
                {shop_condition_sales}
                AND fact_sales.date_created >= CAST(:date_from AS date)
                AND fact_sales.date_created < CAST(:date_to AS date) + INTERVAL '1 day'
            GROUP BY date_created::date
            ORDER BY day ASC
        """)
        result_sales = db.execute(query_sales, params_sales)
        rows_sales = result_sales.fetchall()
        sales_by_day = {}
        for row in rows_sales:
            day = row[0]
            key = day.isoformat() if hasattr(day, 'isoformat') else str(day)
            sales_by_day[key] = (float(row[1] or 0), float(row[2] or 0))
        
        # Merge: for each expense row add commission/logistics from sales_by_day
        points = []
        for row in rows_expenses:
            day = row[0]
            date_str = day.isoformat() if hasattr(day, 'isoformat') else str(day)
            commission, logistics = sales_by_day.get(date_str, (0.0, 0.0))
            points.append(UzumServicesPoint(
                date=date_str,
                storage=float(row[1] or 0),
                ads=float(row[2] or 0),
                fines=float(row[3] or 0),
                commission=commission,
                logistics=logistics
            ))
        
        # Ensure all sales days appear even if no expenses that day
        for date_str in sales_by_day:
            if not any(p.date == date_str for p in points):
                commission, logistics = sales_by_day[date_str]
                points.append(UzumServicesPoint(
                    date=date_str,
                    storage=0.0,
                    ads=0.0,
                    fines=0.0,
                    commission=commission,
                    logistics=logistics
                ))
        points.sort(key=lambda p: p.date)
        
        return UzumServicesDailyResponse(
            points=points,
            period=PeriodInfo(
                code=period_code,
                date_from=date_from_iso or "",
                date_to=date_to_iso
            ),
            filters=UzumServicesFilters(shop_id=shop_id, shop=shop)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_uzum_services_daily: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/charts/orders-sales-daily", response_model=OrdersSalesDailyResponse)
async def get_orders_sales_daily(
    user_id: UUID = Depends(require_user),
    period: str = Query(default="30d", description="Period: 7d, 30d, 90d, or all"),
    shop_id: Optional[str] = Query(default=None, description="Shop UUID"),
    shop: Optional[str] = Query(default=None, description="Shop name (string) for seller-storage filtering by barcode"),
    group_by: str = Query(default="day", description="Grouping: day, week, or month"),
    db: Session = Depends(get_db)
):
    """Get orders and sales chart data grouped by time period (day/week/month).
    
    When shop (string) is set, filter by products in fact_storage_snapshot for that shop (barcode_norm).
    All metrics use the SAME formulas as /api/kpi/summary.
    """
    # Normalize period
    period_code = normalize_period(period)
    
    # Get data_end_date (maximum date from all data tables)
    data_end_date = get_data_end_date(db, user_id)
    
    # Calculate period range based on data_end_date
    period_range_dict = period_range(period_code, data_end_date)
    
    date_to_iso = period_range_dict["date_to"]
    date_to_date = datetime.fromisoformat(date_to_iso).date()
    date_from_iso = period_range_dict["date_from"]
    date_from = datetime.fromisoformat(date_from_iso).date() if date_from_iso else None
    
    shop_norm = normalize_shop(shop)
    
    # For period=all, if date_from is None, use MIN(date_created) or very early date
    if period_code == "all" and date_from is None:
        min_date_query = text(f"""
            SELECT MIN(date_created)::date
            FROM {qname("fact_sales")}
            WHERE user_id = CAST(:user_id AS uuid)
        """)
        min_date_result = db.execute(min_date_query, {"user_id": str(user_id)})
        min_date = min_date_result.scalar()
        if min_date:
            date_from = min_date
        else:
            date_from = date_to_date - timedelta(days=364)
        date_from_iso = date_from.isoformat()
    
    # Ensure date_from is set
    if not date_from:
        date_from = date_to_date - timedelta(days=29)  # Default to 30d
        date_from_iso = date_from.isoformat()
    
    # Normalize shop_id: empty string -> None
    if shop_id == "":
        shop_id = None
    
    # Validate shop_id if provided (only when shop is not used)
    if shop_id and not shop:
        try:
            UUID(shop_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid shop_id format (must be UUID). For seller-storage use 'shop' parameter."
            )
    
    # Normalize group_by
    group_by_normalized = group_by.lower().strip()
    if group_by_normalized not in ("day", "week", "month"):
        group_by_normalized = "day"
    
    logger.info(f"get_orders_sales_daily: user_id={user_id}, period={period_code}, shop_id={shop_id}, shop={shop}, shop_norm={shop_norm}, group_by={group_by_normalized}, date_from={date_from_iso}, date_to={date_to_iso}")
    
    try:
        # Use the SAME status conditions as in KPI (from shared utility)
        status_conditions = get_status_conditions()
        processing_status_condition = status_conditions['processing']
        completed_status_condition = status_conditions['completed']
        
        # Determine grouping expression based on group_by parameter (use alias for correlation)
        if group_by_normalized == "week":
            period_date_expr = "date_trunc('week', fact_sales.date_created)::date"
            period_date_alias = "period_date"
        elif group_by_normalized == "month":
            period_date_expr = "date_trunc('month', fact_sales.date_created)::date"
            period_date_alias = "period_date"
        else:  # day (default)
            period_date_expr = "fact_sales.date_created::date"
            period_date_alias = "period_date"
        
        # Build parameters
        params = {
            "user_id": str(user_id),
            "date_from": date_from_iso,
            "date_to": date_to_iso
        }
        
        # Shop filter: единый helper (storage barcode или shop_id)
        shop_condition_frag, shop_params = shop_filter_condition(shop, shop_id, outer_table_alias="fact_sales")
        params.update(shop_params)
        shop_condition = f"AND {shop_condition_frag}" if shop_condition_frag else ""
        
        # Get SQL expressions for metrics (table_alias for fact_sales)
        metrics_sql = get_sales_metrics_sql(table_alias="fact_sales")
        
        # Build query - FROM with alias fact_sales for EXISTS correlation
        query = text(f"""
            SELECT 
                {period_date_expr} AS {period_date_alias},
                {metrics_sql['orders_qty']} AS orders_qty,
                {metrics_sql['buyouts_qty']} AS buyouts_qty,
                {metrics_sql['returns_qty']} AS returns_qty,
                {metrics_sql['revenue_sum']} AS revenue_sum,
                {get_profit_sql(metrics_sql['revenue_sum'], metrics_sql['commission_sum'], metrics_sql['logistics_sum'], metrics_sql['cogs_sum'])} AS profit_sum,
                {get_avg_check_sql(metrics_sql['revenue_sum'], metrics_sql['orders_qty'])} AS avg_check
            FROM {qname("fact_sales")} fact_sales
            WHERE fact_sales.user_id = CAST(:user_id AS uuid)
                {shop_condition}
                AND fact_sales.date_created >= CAST(:date_from AS date)
                AND fact_sales.date_created < CAST(:date_to AS date) + INTERVAL '1 day'
            GROUP BY {period_date_expr}
            ORDER BY {period_date_expr} ASC
        """)
        
        result = db.execute(query, params)
        rows = result.fetchall()
        logger.info(f"get_orders_sales_daily: found {len(rows)} points")
        
        # Extract points from rows
        points = []
        for row in rows:
            try:
                period_date = row[0]
                date_str = period_date.isoformat() if hasattr(period_date, 'isoformat') else str(period_date)
                orders_qty = float(row[1]) if row[1] is not None else 0.0
                buyouts_qty = float(row[2]) if row[2] is not None else 0.0
                returns_qty = float(row[3]) if row[3] is not None else 0.0
                revenue_sum = float(row[4]) if row[4] is not None else 0.0
                profit_sum = float(row[5]) if row[5] is not None else 0.0
                avg_check = float(row[6]) if row[6] is not None else 0.0
                
                points.append(OrdersSalesDailyPoint(
                    date=date_str,
                    orders_qty=orders_qty,
                    buyouts_qty=buyouts_qty,
                    returns_qty=returns_qty,
                    stock_qty=0.0,  # Складские остатки убраны из графика (always 0.0 for backward compatibility)
                    revenue_sum=revenue_sum,
                    profit_sum=profit_sum,
                    avg_check=avg_check
                ))
            except (IndexError, ValueError, TypeError) as e:
                logger.warning(f"Error parsing row in orders-sales-daily: {e}, row: {row}")
                continue
        
        # Return response
        return OrdersSalesDailyResponse(
            points=points,
            period=PeriodInfo(
                code=period_code,
                date_from=date_from_iso or "",
                date_to=date_to_iso
            ),
            filters=OrdersSalesDailyFilters(shop_id=shop_id, shop=shop)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_orders_sales_daily: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/charts/daily-summary", response_model=DailySummaryResponse)
async def get_daily_summary(
    user_id: UUID = Depends(require_user),
    period: str = Query(default="30d", description="Period: 7d, 30d, 90d, or all"),
    shop_id: Optional[str] = Query(default=None, description="Shop UUID"),
    shop: Optional[str] = Query(default=None, description="Shop name (string) for seller-storage filtering by barcode"),
    db: Session = Depends(get_db)
):
    """Get daily summary table (По дням — Данные по дням). Same formulas as Сводка, GROUP BY day.
    Filters: period (date_from/date_to inclusive), shop (seller-storage Магазин → barcode filter).
    Sources: fact_sales (orders, buys, returns, revenue, commission, logistics, cogs),
    fact_expenses (Хранение/Реклама/Штрафы — УСЛУГИ UZUM, same logic as Сводка, GROUP BY date_written_off::date).
    Налоги = 0.01 * Выручка (per day). Прибыль = revenue - commission - logistics - storage - ads - penalties - cogs - taxes.
    """
    period_code = normalize_period(period)
    data_end_date = get_data_end_date(db, user_id)
    period_range_dict = period_range(period_code, data_end_date)
    date_to_iso = period_range_dict["date_to"]
    date_to_date = datetime.fromisoformat(date_to_iso).date()
    date_from_iso = period_range_dict["date_from"]
    date_from = datetime.fromisoformat(date_from_iso).date() if date_from_iso else None

    if period_code == "all" and date_from is None:
        min_date_result = db.execute(
            text(f"SELECT MIN(date_created)::date FROM {qname('fact_sales')} WHERE user_id = CAST(:user_id AS uuid)"),
            {"user_id": str(user_id)},
        )
        min_date = min_date_result.scalar()
        if min_date:
            date_from = min_date
        else:
            date_from = date_to_date - timedelta(days=364)
        date_from_iso = date_from.isoformat()

    if not date_from:
        date_from = date_to_date - timedelta(days=29)
        date_from_iso = date_from.isoformat()

    if shop_id == "":
        shop_id = None
    if shop_id and not shop:
        try:
            UUID(shop_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid shop_id. For seller-storage use 'shop' parameter.")

    shop_norm = normalize_shop(shop)
    shop_condition_frag, shop_params = shop_filter_condition(shop, shop_id, outer_table_alias="fs")
    params = {
        "user_id": str(user_id),
        "date_from": date_from_iso,
        "date_to": date_to_iso,
    }
    params.update(shop_params)
    shop_condition = f"AND {shop_condition_frag}" if shop_condition_frag else ""

    metrics_sql = get_sales_metrics_sql(table_alias="fs")

    # УСЛУГИ UZUM: Хранение/Реклама/Штрафы из fact_expenses (тот же источник и формулы, что в Сводке), GROUP BY date_written_off::date
    try:
        query = text(f"""
            WITH
            days AS (
                SELECT generate_series(
                    CAST(:date_from AS date),
                    CAST(:date_to AS date),
                    INTERVAL '1 day'
                )::date AS day
            ),
            sales_by_day AS (
                SELECT
                    fs.date_created::date AS day,
                    {metrics_sql['orders_qty']} AS orders_qty,
                    {metrics_sql['buyouts_qty']} AS buyouts_qty,
                    {metrics_sql['returns_qty']} AS returns_qty,
                    {metrics_sql['revenue_sum']} AS revenue_sum,
                    {metrics_sql['commission_sum']} AS commission_sum,
                    {metrics_sql['logistics_sum']} AS logistics_sum,
                    {metrics_sql['cogs_sum']} AS cogs_sum
                FROM {qname('fact_sales')} fs
                WHERE fs.user_id = CAST(:user_id AS uuid)
                    {shop_condition}
                    AND fs.date_created >= CAST(:date_from AS date)
                    AND fs.date_created < CAST(:date_to AS date) + INTERVAL '1 day'
                GROUP BY fs.date_created::date
            ),
            services_by_day AS (
                SELECT
                    fe.date_written_off::date AS day,
                    COALESCE(SUM(
                        CASE
                            WHEN lower(trim(COALESCE(fe.operation_type, ''))) = 'оплата' THEN COALESCE(fe.cost_sum, 0)
                            WHEN lower(trim(COALESCE(fe.operation_type, ''))) = 'возврат' THEN -COALESCE(fe.cost_sum, 0)
                            ELSE 0
                        END
                    ), 0) AS storage,
                    COALESCE(SUM(
                        CASE
                            WHEN (COALESCE(fe.source, '') ILIKE '%маркетинг%' OR COALESCE(fe.source, '') ILIKE '%marketing%')
                                 AND (COALESCE(fe.operation_type, '') ILIKE '%оплат%' OR COALESCE(fe.operation_type, '') ILIKE '%payment%')
                            THEN COALESCE(fe.cost_sum, 0)
                            ELSE 0
                        END
                    ), 0) AS ads,
                    COALESCE(SUM(
                        CASE WHEN COALESCE(fe.service, '') ILIKE '%штраф%' THEN COALESCE(fe.amount_sum, 0) ELSE 0 END
                    ), 0) AS penalties
                FROM {qname('fact_expenses')} fe
                WHERE fe.user_id = CAST(:user_id AS uuid)
                    AND fe.date_written_off >= CAST(:date_from AS date)
                    AND fe.date_written_off < CAST(:date_to AS date) + INTERVAL '1 day'
                GROUP BY fe.date_written_off::date
            )
            SELECT
                d.day AS date,
                COALESCE(s.orders_qty, 0) AS orders,
                COALESCE(s.buyouts_qty, 0) AS buys,
                COALESCE(s.returns_qty, 0) AS returns,
                COALESCE(s.revenue_sum, 0) AS revenue,
                COALESCE(s.commission_sum, 0) AS commission,
                COALESCE(s.logistics_sum, 0) AS logistics,
                COALESCE(sv.storage, 0) AS storage,
                COALESCE(sv.ads, 0) AS ads,
                COALESCE(sv.penalties, 0) AS penalties,
                COALESCE(s.cogs_sum, 0) AS cogs,
                ROUND(COALESCE(s.revenue_sum, 0) * 0.01, 2) AS taxes,
                (COALESCE(s.revenue_sum, 0) - COALESCE(s.commission_sum, 0) - COALESCE(s.logistics_sum, 0)
                 - COALESCE(sv.storage, 0) - COALESCE(sv.ads, 0) - COALESCE(sv.penalties, 0)
                 - COALESCE(s.cogs_sum, 0) - ROUND(COALESCE(s.revenue_sum, 0) * 0.01, 2)) AS profit
            FROM days d
            LEFT JOIN sales_by_day s ON d.day = s.day
            LEFT JOIN services_by_day sv ON d.day = sv.day
            ORDER BY d.day ASC
        """)
        result = db.execute(query, params)
        rows = result.fetchall()
        logger.info(f"get_daily_summary: found {len(rows)} days, period={period_code}, shop_norm={shop_norm}")

        points = []
        for row in rows:
            try:
                day = row[0]
                date_str = day.isoformat() if hasattr(day, "isoformat") else str(day)
                points.append(DailySummaryPoint(
                    date=date_str,
                    orders=float(row[1] or 0),
                    buys=float(row[2] or 0),
                    returns=float(row[3] or 0),
                    revenue=float(row[4] or 0),
                    commission=float(row[5] or 0),
                    logistics=float(row[6] or 0),
                    storage=float(row[7] or 0),
                    ads=float(row[8] or 0),
                    penalties=float(row[9] or 0),
                    cogs=float(row[10] or 0),
                    taxes=float(row[11] or 0),
                    profit=float(row[12] or 0),
                ))
            except (IndexError, ValueError, TypeError) as e:
                logger.warning(f"daily-summary parse row: {e}, row={row}")
                continue

        return DailySummaryResponse(
            points=points,
            period=PeriodInfo(code=period_code, date_from=date_from_iso or "", date_to=date_to_iso),
            filters=DailySummaryFilters(shop_id=shop_id, shop=shop),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_daily_summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
