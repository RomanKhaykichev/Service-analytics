from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from uuid import UUID
from datetime import datetime
import logging
from app.db import get_db, qname
from app.deps import require_user
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
    period: str = Query(default="30d", regex="^(30d|90d|365d|custom)$"),
    date_from: Optional[str] = Query(default=None, description="ISO date (YYYY-MM-DD), required for custom period"),
    date_to: Optional[str] = Query(default=None, description="ISO date (YYYY-MM-DD), required for custom period"),
    shop_id: Optional[str] = Query(default=None, description="Shop UUID"),
    db: Session = Depends(get_db)
):
    """Get daily revenue chart data from v_sales_daily."""
    logger.info(f"get_revenue_daily: user_id={user_id}, period={period}, shop_id={shop_id}")
    
    # Validate custom period
    if period == "custom":
        if not date_from or not date_to:
            raise HTTPException(
                status_code=400,
                detail="date_from and date_to are required for custom period"
            )
        try:
            date_from_obj = datetime.fromisoformat(date_from).date()
            date_to_obj = datetime.fromisoformat(date_to).date()
            if date_from_obj > date_to_obj:
                raise HTTPException(
                    status_code=400,
                    detail="date_from must be <= date_to"
                )
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date format: {str(e)}. Use YYYY-MM-DD"
            )
    
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
        
        # Add date filter based on period
        if period == "30d":
            conditions.append("day >= CURRENT_DATE - INTERVAL '30 days'")
        elif period == "90d":
            conditions.append("day >= CURRENT_DATE - INTERVAL '90 days'")
        elif period == "365d":
            conditions.append("day >= CURRENT_DATE - INTERVAL '365 days'")
        elif period == "custom":
            conditions.append("day BETWEEN CAST(:date_from AS date) AND CAST(:date_to AS date)")
            params["date_from"] = date_from
            params["date_to"] = date_to
        
        # Build query
        where_clause = " AND ".join(conditions)
        query = text(f"""
            SELECT 
                day::text as date,
                SUM(revenue_net_sum) as value
            FROM {qname("v_sales_daily")}
            WHERE {where_clause}
            GROUP BY day
            ORDER BY day ASC
        """)
        
        result = db.execute(query, params)
        rows = result.fetchall()
        logger.info(f"get_revenue_daily: found {len(rows)} rows")
        
        # Extract date and value from rows
        points = []
        for row in rows:
            try:
                date_str = str(row[0]) if row[0] else ""
                value = float(row[1]) if row[1] is not None else 0.0
                points.append(RevenuePoint(date=date_str, value=value))
            except (IndexError, ValueError, TypeError) as e:
                logger.warning(f"Error parsing row in revenue-daily: {e}, row: {row}")
                continue
        
        # Calculate actual date range from data
        if points:
            actual_date_from = points[0].date
            actual_date_to = points[-1].date
        else:
            actual_date_from = date_from if period == "custom" else ""
            actual_date_to = date_to if period == "custom" else ""
        
        return RevenueDailyResponse(
            points=points,
            period=PeriodInfo(
                code=period,
                date_from=actual_date_from,
                date_to=actual_date_to
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
