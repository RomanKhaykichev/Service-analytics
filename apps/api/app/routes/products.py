from fastapi import APIRouter, Query, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from uuid import UUID
import logging
from app.db import get_db, qname
from app.deps import require_user
from app.schemas import ProductsResponse, PeriodInfo, Filters, Paging, ProductItem

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/products", response_model=ProductsResponse)
async def get_products(
    request: Request,
    period: str = Query(default="30d", regex="^(7d|30d|60d|90d|all)$"),
    shop_id: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    sort: str = Query(default="revenue", regex="^(revenue|profit|returns|stock|turnover)$"),
    order: str = Query(default="desc", regex="^(asc|desc)$"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """Get top products with sales data from v_sales_daily."""
    user_id = require_user(request)
    
    try:
        # Simplified query: top products by revenue from v_sales_daily
        # Group by sku/name and sum revenue
        query = text(f"""
            SELECT 
                COALESCE(sku, barcode::text) AS sku,
                COALESCE(product_name, 'Unknown') AS product_name,
                COALESCE(category, '') AS category,
                SUM(orders_cnt) AS orders_cnt,
                SUM(qty) AS qty,
                SUM(returns_qty) AS returns_qty,
                SUM(revenue_sum) AS revenue_sum,
                SUM(commission_sum) AS commission_sum,
                SUM(logistics_sum) AS logistics_sum,
                SUM(promo_sum) AS promo_sum,
                SUM(cogs_sum) AS cogs_sum,
                (SUM(revenue_sum) - SUM(commission_sum) - SUM(logistics_sum) - SUM(promo_sum) - SUM(cogs_sum)) AS profit_sum,
                MAX(barcode::text) AS barcode,
                COUNT(*) OVER() AS total
            FROM {qname("v_sales_daily")}
            WHERE user_id = CAST(:user_id AS uuid)
            GROUP BY COALESCE(sku, barcode::text), COALESCE(product_name, 'Unknown'), COALESCE(category, '')
            ORDER BY SUM(revenue_sum) DESC
            LIMIT :limit OFFSET :offset
        """)
        
        params = {
            "user_id": str(user_id),
            "limit": limit,
            "offset": offset
        }
        
        result = db.execute(query, params)
        rows = result.fetchall()
        
        # Get total count
        total = int(rows[0][-1]) if rows else 0
        
        items = []
        for row in rows:
            try:
                revenue_sum = float(row[6]) if row[6] else 0.0
                profit_sum = float(row[11]) if row[11] else 0.0
                margin_ratio = (profit_sum / revenue_sum) if revenue_sum > 0 else None
                
                items.append(ProductItem(
                    barcode=str(row[12]) if len(row) > 12 and row[12] else "",
                    sku=str(row[0]) if row[0] else "",
                    product_name=str(row[1]) if row[1] else "Unknown",
                    category=str(row[2]) if row[2] else None,
                    orders_cnt=int(row[3]) if row[3] else 0,
                    qty=int(row[4]) if row[4] else 0,
                    returns_qty=int(row[5]) if row[5] else 0,
                    revenue_sum=revenue_sum,
                    profit_sum=profit_sum,
                    margin_ratio=margin_ratio,
                    stock_qty=None,
                    coverage_days=None,
                    turnover_days=None
                ))
            except (IndexError, ValueError, TypeError) as e:
                logger.warning(f"Error parsing row in products: {e}")
                continue
        
        if not items:
            logger.warning("No data found in v_sales_daily for products")
        
        return ProductsResponse(
            period=PeriodInfo(
                code=period,
                date_from="",
                date_to=""
            ),
            filters=Filters(shop_id=shop_id, q=q),
            paging=Paging(limit=limit, offset=offset, total=total),
            items=items
        )
    except Exception as e:
        logger.error(f"Error in get_products: {e}")
        # Return empty response on error
        return ProductsResponse(
            period=PeriodInfo(code=period, date_from="", date_to=""),
            filters=Filters(shop_id=shop_id, q=q),
            paging=Paging(limit=limit, offset=offset, total=0),
            items=[]
        )
