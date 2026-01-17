from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db import get_db, qname
from app.deps import require_user
from app.settings import get_settings
from uuid import UUID

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
