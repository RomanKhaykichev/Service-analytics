from fastapi import APIRouter, Request, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db import get_db, qname
from app.deps import require_user
from app.settings import get_settings
from uuid import UUID
from typing import Optional
from datetime import datetime, timedelta

router = APIRouter()
settings = get_settings()


@router.get("/debug/db")
async def debug_db(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Debug endpoint to check database connection and schema configuration.
    Requires authentication (JWT or X-User-Id header).
    """
    # Require authentication
    user_id = require_user(request)
    
    try:
        # Get current database name
        db_result = db.execute(text("SELECT current_database()"))
        current_database = db_result.scalar()
        
        # Get current search_path (schema search path)
        search_path_result = db.execute(text("SHOW search_path"))
        search_path = search_path_result.scalar()
        
        # Get counts from views
        counts = {}
        
        # Count from v_sales_daily
        try:
            sales_count_result = db.execute(text(f"SELECT COUNT(*) FROM {qname('v_sales_daily')} WHERE user_id = CAST(:user_id AS uuid)"), {"user_id": str(user_id)})
            counts["v_sales_daily"] = sales_count_result.scalar()
        except Exception as e:
            counts["v_sales_daily"] = f"Error: {str(e)}"
        
        # Count from v_product_current_stock
        try:
            stock_count_result = db.execute(text(f"SELECT COUNT(*) FROM {qname('v_product_current_stock')} WHERE user_id = CAST(:user_id AS uuid)"), {"user_id": str(user_id)})
            counts["v_product_current_stock"] = stock_count_result.scalar()
        except Exception as e:
            counts["v_product_current_stock"] = f"Error: {str(e)}"
        
        # Count from dim_shop (if exists)
        try:
            shop_count_result = db.execute(text(f"SELECT COUNT(*) FROM {qname('dim_shop')} WHERE user_id = CAST(:user_id AS uuid)"), {"user_id": str(user_id)})
            counts["dim_shop"] = shop_count_result.scalar()
        except Exception as e:
            counts["dim_shop"] = f"Error: {str(e)}"
        
        return {
            "current_database": current_database,
            "current_search_path": search_path,
            "db_schema": settings.DB_SCHEMA,
            "user_id": str(user_id),
            "counts": counts,
            "qualified_names": {
                "v_sales_daily": qname("v_sales_daily"),
                "v_product_current_stock": qname("v_product_current_stock"),
                "dim_shop": qname("dim_shop")
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database debug error: {str(e)}"
        )


@router.get("/debug/period")
async def debug_period(
    request: Request,
    period: str = Query(default="30d", description="Period: 7d, 30d, 90d, or all"),
    shop_id: Optional[str] = Query(default=None, description="Shop UUID"),
    db: Session = Depends(get_db)
):
    """
    Debug endpoint to check period range calculation.
    Returns: ok, user_id, period, shop_id, period_range, data_end_date, year_start, price_window_from, price_window_to.
    """
    from app.routes.kpi import get_data_end_date, period_range, normalize_period
    
    user_id = require_user(request)
    
    # Validate shop_id if provided
    if shop_id:
        try:
            UUID(shop_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid shop_id format (must be UUID)"
            )
    
    # Normalize period
    period_code = normalize_period(period)
    
    # Get data_end_date
    data_end_date = get_data_end_date(db, user_id)
    
    # Calculate period range
    period_range_dict = period_range(period_code, data_end_date)
    date_to_iso = period_range_dict["date_to"]
    
    # Protection: if date_to is None, use today
    if date_to_iso is None:
        date_to_date = datetime.now().date()
        date_to_iso = date_to_date.isoformat()
    else:
        date_to_date = datetime.fromisoformat(date_to_iso).date()
    
    # Calculate year_start (from date_to)
    year_start = datetime(date_to_date.year, 1, 1).date()
    
    # Calculate price_window_from (90 days before date_to)
    price_window_from = date_to_date - timedelta(days=89)
    
    return {
        "ok": True,
        "user_id": str(user_id),
        "shop_id": shop_id,
        "period": period_code,
        "data_end_date": data_end_date.isoformat(),
        "period_range": period_range_dict,
        "year_start": year_start.isoformat(),
        "price_window_from": price_window_from.isoformat(),
        "price_window_to": date_to_date.isoformat()
    }
