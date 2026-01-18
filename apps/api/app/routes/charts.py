from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta
import logging
from app.db import get_db, qname
from app.deps import require_user
from app.routes.kpi import get_data_end_date, period_range, normalize_period
from app.utils.statuses import get_status_sql_condition
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
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/charts/revenue-daily", response_model=RevenueDailyResponse)
async def get_revenue_daily(
    user_id: UUID = Depends(require_user),
    period: str = Query(default="30d", description="Period: 7d, 30d, 90d, or all"),
    shop_id: Optional[str] = Query(default=None, description="Shop UUID"),
    db: Session = Depends(get_db)
):
    """Get daily revenue chart data from fact_sales with revenue, orders, and averageCheck."""
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
    
    logger.info(f"get_revenue_daily: user_id={user_id}, period={period_code}, shop_id={shop_id}, period_range={period_range_dict}")
    
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
        # Get status conditions
        completed_condition = get_status_sql_condition('completed')
        orders_condition = get_status_sql_condition('orders')  # всё кроме отмен
        
        # Build parameters
        params = {
            "user_id": str(user_id),
            "date_to": date_to_iso
        }
        
        # Build shop_id filter condition
        shop_condition = ""
        if shop_id:
            params["shop_id"] = shop_id
            shop_condition = "AND shop_id = CAST(:shop_id AS uuid)"
        
        # Build date_from condition
        date_from_condition = ""
        if date_from:
            params["date_from"] = date_from.isoformat()
            date_from_condition = "AND date_created >= CAST(:date_from AS date)"
        
        # Build query - агрегируем по d = date_created::date
        query = text(f"""
            SELECT 
                date_created::date AS day,
                COALESCE(SUM(CASE WHEN ({completed_condition}) THEN revenue_sum ELSE 0 END), 0) AS revenue,
                COALESCE(SUM(CASE WHEN ({orders_condition}) THEN qty ELSE 0 END), 0) AS orders,
                COALESCE(SUM(CASE WHEN ({completed_condition}) THEN qty ELSE 0 END), 0) AS completed_qty
            FROM {qname("fact_sales")}
            WHERE user_id = CAST(:user_id AS uuid)
                {shop_condition}
                {date_from_condition}
                AND date_created < CAST(:date_to AS date) + INTERVAL '1 day'
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
            filters=RevenueFilters(shop_id=shop_id)
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
    q: Optional[str] = Query(default=None, description="Search in sku, product_name, barcode"),
    db: Session = Depends(get_db)
):
    """Get current stock snapshot from v_product_current_stock."""
    logger.info(f"get_stock_current: user_id={user_id}, shop_id={shop_id}, q={q}")
    
    try:
        # Build WHERE conditions
        conditions = ["user_id = CAST(:user_id AS uuid)"]
        params = {"user_id": str(user_id)}
        
        # Add shop_id filter if provided
        if shop_id:
            try:
                UUID(shop_id)  # Validate UUID format
                conditions.append("shop_id = CAST(:shop_id AS uuid)")
                params["shop_id"] = shop_id
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid shop_id format (must be UUID)"
                )
        
        # Add search filter if provided
        if q:
            conditions.append("(sku ILIKE :q OR product_name ILIKE :q OR barcode ILIKE :q)")
            params["q"] = f"%{q}%"
        
        # Build query - select all available fields from view
        where_clause = " AND ".join(conditions)
        query = text(f"""
            SELECT 
                barcode,
                sku,
                product_name,
                stock_qty,
                coverage_days,
                turnover_days,
                fee_total_30d,
                storage_type,
                size_group
            FROM {qname("v_product_current_stock")}
            WHERE {where_clause}
            ORDER BY stock_qty DESC NULLS LAST, fee_total_30d DESC NULLS LAST
            LIMIT 200
        """)
        
        result = db.execute(query, params)
        rows = result.fetchall()
        logger.info(f"get_stock_current: found {len(rows)} rows")
        
        items = []
        for row in rows:
            try:
                # Handle variable number of columns gracefully
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
            logger.warning("No data found in v_product_current_stock for stock-current chart")
        
        return StockCurrentResponse(
            items=items,
            filters=StockFilters(shop_id=shop_id, q=q or "")
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
