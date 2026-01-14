import logging
import os
from fastapi import APIRouter, Request, HTTPException, Query
from app.auth import get_user_id
from app.db import execute_all, execute_one
from app.schemas import ChartRevenueDailyResponse, ChartStockCurrentResponse, PeriodInfo, Filters, ChartPoint, StockItem
from app.utils import parse_period, normalize_shop_id

logger = logging.getLogger(__name__)
router = APIRouter()

# Check if we're in dev mode (simple check via environment variable)
IS_DEV = os.getenv("ENV", "development").lower() in ("development", "dev", "local")


@router.get("/charts/revenue-daily", response_model=ChartRevenueDailyResponse)
async def get_revenue_daily(
    request: Request,
    period: str = Query(default="30d", regex="^(7d|30d|60d|90d|all)$"),
    shop_id: str = Query(default=None)
):
    """Get daily revenue chart data."""
    user_id = get_user_id(request)
    
    try:
        date_from, date_to, code = parse_period(period)
        shop_id_normalized = normalize_shop_id(shop_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    query = """
        SELECT 
          day::text AS day, 
          COALESCE(sum(revenue_sum), 0) AS revenue_sum
        FROM app.v_kpi_filtered_daily
        WHERE user_id = %(user_id)s
          AND (shop_id = COALESCE(CAST(%(shop_id)s AS uuid), shop_id))
          AND day BETWEEN %(date_from)s AND %(date_to)s
        GROUP BY day
        ORDER BY day
    """
    
    rows = execute_all(query, {
        "user_id": user_id,
        "shop_id": shop_id_normalized,
        "date_from": date_from,
        "date_to": date_to
    })
    
    points = [
        ChartPoint(day=row["day"], revenue_sum=float(row["revenue_sum"]))
        for row in rows
    ]
    
    return ChartRevenueDailyResponse(
        period=PeriodInfo(
            code=code,
            date_from=date_from.isoformat(),
            date_to=date_to.isoformat()
        ),
        filters=Filters(shop_id=shop_id_normalized),
        points=points
    )


@router.get("/charts/stock-current", response_model=ChartStockCurrentResponse)
async def get_stock_current(
    request: Request,
    shop_id: str = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000)
):
    """Get current stock snapshot."""
    user_id = get_user_id(request)
    
    try:
        shop_id_normalized = normalize_shop_id(shop_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Debug: Get current batch info (dev mode only)
    current_batch_id = None
    if IS_DEV:
        batch_query = """
            SELECT upload_batch_id, created_at
            FROM app.v_current_batch
            WHERE user_id = %(user_id)s
            LIMIT 1
        """
        batch_row = execute_one(batch_query, {"user_id": user_id})
        if batch_row:
            current_batch_id = str(batch_row.get("upload_batch_id", ""))
            logger.info(
                f"[stock-current] user_id={user_id}, shop_id={shop_id_normalized}, "
                f"current_batch_id={current_batch_id}"
            )
    
    query = """
        SELECT
          barcode::text AS barcode,
          sku::text AS sku,
          product_name::text AS product_name,
          stock_qty,
          coverage_days,
          turnover_days
        FROM app.v_product_current_stock
        WHERE user_id = %(user_id)s
          AND (shop_id = COALESCE(CAST(%(shop_id)s AS uuid), shop_id))
        ORDER BY stock_qty DESC NULLS LAST
        LIMIT %(limit)s
    """
    
    rows = execute_all(query, {
        "user_id": user_id,
        "shop_id": shop_id_normalized,
        "limit": limit
    })
    
    # Debug: Log row count and sample data (dev mode only)
    if IS_DEV:
        row_count = len(rows)
        non_null_stock_qty = sum(1 for r in rows if r.get("stock_qty") is not None)
        non_null_coverage_days = sum(1 for r in rows if r.get("coverage_days") is not None)
        non_null_turnover_days = sum(1 for r in rows if r.get("turnover_days") is not None)
        logger.info(
            f"[stock-current] Found {row_count} rows: "
            f"stock_qty={non_null_stock_qty}/{row_count}, "
            f"coverage_days={non_null_coverage_days}/{row_count}, "
            f"turnover_days={non_null_turnover_days}/{row_count}"
        )
        if rows and row_count > 0:
            sample = rows[0]
            logger.debug(
                f"[stock-current] Sample row: barcode={sample.get('barcode')}, "
                f"stock_qty={sample.get('stock_qty')}, "
                f"coverage_days={sample.get('coverage_days')}, "
                f"turnover_days={sample.get('turnover_days')}"
            )
    
    items = [
        StockItem(
            barcode=row["barcode"],
            sku=row["sku"],
            product_name=row["product_name"],
            stock_qty=float(row["stock_qty"]) if row["stock_qty"] is not None else None,
            coverage_days=float(row["coverage_days"]) if row["coverage_days"] is not None else None,
            turnover_days=float(row["turnover_days"]) if row["turnover_days"] is not None else None
        )
        for row in rows
    ]
    
    return ChartStockCurrentResponse(
        filters=Filters(shop_id=shop_id_normalized),
        items=items
    )
