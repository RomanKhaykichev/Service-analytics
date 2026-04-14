from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db import get_db, qname
from app.deps import require_user
from app.settings import get_settings
from app.utils.shop_filter import normalize_shop
from uuid import UUID
from typing import Optional
from datetime import datetime, timedelta

router = APIRouter()
settings = get_settings()


@router.get("/debug/db")
async def debug_db(
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Debug endpoint to check database connection and schema configuration.
    Requires authentication (JWT or X-User-Id header).
    """
    
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


@router.get("/debug/shop-filter")
async def debug_shop_filter(
    shop: Optional[str] = Query(default=None, description="Shop name (seller-storage) to diagnose"),
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Diagnostic: which shop/shop_norm was received and how many barcodes fall into the shop set.
    Dev-only helper to verify shop filter is applied consistently.
    """
    shop_norm = normalize_shop(shop)
    barcode_count = None
    if shop_norm:
        try:
            r = db.execute(
                text(f"""
                    SELECT COUNT(DISTINCT COALESCE(barcode_norm, NULLIF(TRIM(regexp_replace(CAST(barcode AS text), '\\s+', '', 'g')), '')))
                    FROM {qname("fact_storage_snapshot")}
                    WHERE user_id = CAST(:user_id AS uuid)
                      AND upper(regexp_replace(trim(COALESCE(shop_raw, '')), '\\s+', ' ', 'g')) = :shop_norm
                """),
                {"user_id": str(user_id), "shop_norm": shop_norm}
            )
            barcode_count = r.scalar()
        except Exception as e:
            barcode_count = f"Error: {e}"
    return {
        "shop": shop,
        "shop_norm": shop_norm,
        "barcode_count_in_shop_set": barcode_count,
        "user_id": str(user_id),
    }


@router.get("/debug/period")
async def debug_period(
    period: str = Query(default="30d", description="Period: 7d, 30d, 90d, or all"),
    shop_id: Optional[str] = Query(default=None, description="Shop UUID"),
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Debug endpoint to check period range calculation.
    Returns: ok, user_id, period, shop_id, period_range, data_end_date, year_start, price_window_from, price_window_to.
    """
    from app.routes.kpi import get_data_end_date, period_range, normalize_period
    
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


@router.get("/debug/stock")
async def debug_stock(
    shop_id: Optional[str] = Query(default=None, description="Shop UUID"),
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Debug endpoint to check stock calculation from fact_leftout_snapshot.
    Returns: last_loaded_at, stockQuantity, rows_cnt, rows_with_stock (marketplace_side>0).
    """
    
    # Validate shop_id if provided
    if shop_id:
        try:
            UUID(shop_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid shop_id format (must be UUID)"
            )
    
    stock_params = {
        "user_id": str(user_id),
        "shop_id": shop_id
    }
    
    try:
        # Get latest snapshot loaded_at
        max_loaded_query = text(f"""
            SELECT MAX(loaded_at) AS snap_loaded_at
            FROM {qname("fact_leftout_snapshot")}
            WHERE user_id = CAST(:user_id AS uuid)
                AND (:shop_id IS NULL OR shop_id = CAST(:shop_id AS uuid))
        """)
        
        max_loaded_result = db.execute(max_loaded_query, stock_params)
        snap_loaded_at = max_loaded_result.scalar()
        
        if not snap_loaded_at:
            return {
                "ok": True,
                "user_id": str(user_id),
                "shop_id": shop_id,
                "last_loaded_at": None,
                "stockQuantity": 0,
                "rows_cnt": 0,
                "rows_with_stock": 0,
                "message": "No snapshot data found"
            }
        
        stock_params["snap_loaded_at"] = snap_loaded_at
        
        # Get stock aggregates
        stock_agg_query = text(f"""
            SELECT 
                COUNT(*) AS rows_cnt,
                SUM(COALESCE(marketplace_side, 0)) AS stock_quantity,
                SUM(CASE WHEN COALESCE(marketplace_side, 0) > 0 THEN 1 ELSE 0 END) AS rows_with_stock
            FROM {qname("fact_leftout_snapshot")}
            WHERE user_id = CAST(:user_id AS uuid)
                AND (:shop_id IS NULL OR shop_id = CAST(:shop_id AS uuid))
                AND loaded_at = CAST(:snap_loaded_at AS timestamp)
        """)
        
        stock_agg_result = db.execute(stock_agg_query, stock_params)
        stock_agg_row = stock_agg_result.fetchone()
        
        if stock_agg_row:
            rows_cnt = int(stock_agg_row[0] or 0)
            stock_quantity = float(stock_agg_row[1] or 0)
            rows_with_stock = int(stock_agg_row[2] or 0)
        else:
            rows_cnt = 0
            stock_quantity = 0.0
            rows_with_stock = 0
        
        return {
            "ok": True,
            "user_id": str(user_id),
            "shop_id": shop_id,
            "last_loaded_at": snap_loaded_at.isoformat() if snap_loaded_at and hasattr(snap_loaded_at, 'isoformat') else (str(snap_loaded_at) if snap_loaded_at else None),
            "stockQuantity": stock_quantity,
            "rows_cnt": rows_cnt,
            "rows_with_stock": rows_with_stock
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Stock debug error: {str(e)}"
        )


