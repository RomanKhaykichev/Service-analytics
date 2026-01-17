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
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/charts/revenue-daily", response_model=RevenueDailyResponse)
async def get_revenue_daily(
    user_id: UUID = Depends(require_user),
    period: str = Query(default="30d", description="Period: 7d, 30d, 90d, or all"),
    shop_id: Optional[str] = Query(default=None, description="Shop UUID"),
    mode: str = Query(default="completed", description="Mode: completed (only completed) or orders (all except cancelled)"),
    db: Session = Depends(get_db)
):
    """Get daily revenue chart data from fact_sales."""
    # Normalize period
    period_code = normalize_period(period)
    
    # Get data_end_date (maximum date from all data tables)
    data_end_date = get_data_end_date(db, user_id)
    
    # For period=all, use 365d before date_to to avoid huge datasets
    if period_code == "all":
        date_from_for_chart = data_end_date - timedelta(days=365)
        period_range_dict = {
            "code": period_code,
            "date_from": date_from_for_chart.isoformat(),
            "date_to": data_end_date.isoformat()
        }
    else:
        # Calculate period range based on data_end_date
        period_range_dict = period_range(period_code, data_end_date)
    
    date_to_iso = period_range_dict["date_to"]
    date_to_date = datetime.fromisoformat(date_to_iso).date()
    date_from_iso = period_range_dict["date_from"]
    date_from = datetime.fromisoformat(date_from_iso).date() if date_from_iso else None
    
    # Validate mode
    if mode not in ['completed', 'orders']:
        raise HTTPException(
            status_code=400,
            detail="Invalid mode. Must be 'completed' or 'orders'"
        )
    
    logger.info(f"get_revenue_daily: user_id={user_id}, period={period_code}, shop_id={shop_id}, mode={mode}, period_range={period_range_dict}")
    
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
        # Ensure date_from is set for query (for period=all use 365d range)
        if not date_from:
            # For period=all, date_from was already set to 365 days before
            # But if somehow it's None, use 365 days before date_to
            date_from = date_to_date - timedelta(days=365)
            date_from_iso = date_from.isoformat()
        
        # Get status condition based on mode
        status_condition = get_status_sql_condition(mode)
        
        # Build parameters
        params = {
            "user_id": str(user_id),
            "date_from": date_from.isoformat(),
            "date_to": date_to_iso
        }
        
        # Build shop_id filter condition
        shop_condition = ""
        if shop_id:
            params["shop_id"] = shop_id
            shop_condition = "AND shop_id = CAST(:shop_id AS uuid)"
        
        # Build query with generate_series to always return full calendar
        query = text(f"""
            SELECT 
                d.day::date AS day,
                COALESCE(sales.revenue_sum, 0) AS value
            FROM (
                SELECT generate_series(
                    CAST(:date_from AS date),
                    CAST(:date_to AS date),
                    INTERVAL '1 day'
                )::date AS day
            ) d
            LEFT JOIN (
                SELECT 
                    date_trunc('day', date_created)::date AS day,
                    SUM(revenue_sum) AS revenue_sum
                FROM {qname("fact_sales")}
                WHERE user_id = CAST(:user_id AS uuid)
                    AND ({status_condition})
                    {shop_condition}
                    AND date_created >= CAST(:date_from AS date)
                    AND date_created < CAST(:date_to AS date) + INTERVAL '1 day'
                GROUP BY date_trunc('day', date_created)::date
            ) sales ON sales.day = d.day
            ORDER BY d.day ASC
        """)
        
        result = db.execute(query, params)
        rows = result.fetchall()
        logger.info(f"get_revenue_daily: found {len(rows)} rows")
        
        # Extract date and value from rows
        points = []
        for row in rows:
            try:
                day = row[0]
                date_str = day.isoformat() if hasattr(day, 'isoformat') else str(day)
                value = float(row[1]) if row[1] is not None else 0.0
                points.append(RevenuePoint(date=date_str, value=value))
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
