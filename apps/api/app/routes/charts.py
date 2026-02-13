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
from app.settings import get_settings
from app.routes.kpi import get_data_end_date, period_range, normalize_period, resolve_date_range
from app.utils.statuses import get_status_sql_condition

# SQL condition for "status = Завершен" (completed)
_STATUS_COMPLETED_SQL = " (status ILIKE '%заверш%' OR status ILIKE '%достав%' OR status ILIKE '%получ%' OR status ILIKE '%выдан%') "
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
    ShipmentRecommendationsResponse,
    ShipmentRecommendationItem,
    ProductsTableResponse,
    ProductsTableItem,
)
from app.schemas.charts import ProductCommentResponse, ProductCommentRequest

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


@router.get("/charts/revenue-daily", response_model=RevenueDailyResponse)
async def get_revenue_daily(
    user_id: UUID = Depends(require_user),
    period: str = Query(default="30d", description="Period: 7d, 30d, 90d, or all"),
    date_from: Optional[str] = Query(default=None, description="Start date YYYY-MM-DD (overrides period when date_to also set)"),
    date_to: Optional[str] = Query(default=None, description="End date YYYY-MM-DD"),
    shop_id: Optional[str] = Query(default=None, description="Shop UUID (dim_shop)"),
    shop: Optional[str] = Query(default=None, description="Shop name (string) for seller-storage filtering by barcode"),
    product_id: Optional[str] = Query(default=None, description="ID карточки товара — данные только по этому товару (штрихкоды из left-out)"),
    db: Session = Depends(get_db)
):
    """Get daily revenue chart data from fact_sales with revenue, orders, and averageCheck.
    When shop (string) is set, filter by products present in fact_storage_snapshot for that shop (barcode_norm).
    When product_id is set, filter by barcode_norm from stg_leftout_old where ID товара = product_id.
    date_from/date_to (both set) override period; filter by fact_sales.date_created.
    """
    date_from_iso, date_to_iso, date_from, date_to_date, period_code, period_range_dict = resolve_date_range(
        date_from, date_to, period, db, user_id
    )
    shop_norm = normalize_shop(shop)
    logger.info(f"get_revenue_daily: user_id={user_id}, period={period_code}, shop_id={shop_id}, shop={shop}, shop_norm={shop_norm}, product_id={product_id}, period_range={period_range_dict}")
    
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
        completed_condition_raw = get_status_sql_condition('completed')
        orders_condition_raw = get_status_sql_condition('orders')  # всё кроме отмен
        
        # Заменяем 'status' на 'fact_sales.status' для использования в запросе с алиасом
        completed_condition = completed_condition_raw.replace('status', 'fact_sales.status')
        orders_condition = orders_condition_raw.replace('status', 'fact_sales.status')
        
        # Build parameters
        params = {
            "user_id": str(user_id),
            "date_to": date_to_iso
        }
        
        # Shop filter: единый helper (storage barcode или shop_id)
        shop_condition_frag, shop_params = shop_filter_condition(shop, shop_id, outer_table_alias="fact_sales")
        params.update(shop_params)
        shop_condition = f"AND {shop_condition_frag}" if shop_condition_frag else ""

        # Product_id filter: только штрихкоды, принадлежащие карточке (ID товара из left-out)
        product_id_condition = ""
        if product_id and str(product_id).strip():
            params["product_id"] = str(product_id).strip()
            product_id_condition = f"""
                AND fact_sales.barcode_norm IN (
                    SELECT NULLIF(trim(regexp_replace(COALESCE(sl.barcode_raw, ''), '\\s+', '', 'g')), '')
                    FROM {qname("stg_leftout_old")} sl
                    WHERE sl.user_id = CAST(:user_id AS uuid)
                      AND sl.upload_batch_id = (
                          SELECT sl2.upload_batch_id FROM {qname("stg_leftout_old")} sl2
                          WHERE sl2.user_id = CAST(:user_id AS uuid)
                          ORDER BY sl2.upload_batch_id DESC NULLS LAST
                          LIMIT 1
                      )
                      AND NULLIF(trim(sl.data->>'ID товара'), '') = :product_id
                )
            """
        
        # Build date_from condition
        date_from_condition = ""
        if date_from:
            params["date_from"] = date_from.isoformat()
            date_from_condition = "AND fact_sales.date_created >= CAST(:date_from AS date)"
        
        # На карточке товара (product_id задан): Заказы, Возвраты, Выручка, Прибыль по формулам из блоков Продажи и Финансы.
        has_product_filter = bool(product_id and str(product_id).strip())
        orders_agg_sql = (
            "COALESCE(SUM(COALESCE(fact_sales.qty, 0)), 0)"
            if has_product_filter
            else f"COALESCE(SUM(CASE WHEN ({orders_condition}) THEN fact_sales.qty ELSE 0 END), 0)"
        )
        
        if has_product_filter:
            # Возвраты = SUM(returns_qty); Прибыль = выручка − cogs − commission − logistics − 1% с выручки
            extra_select = f"""
                , COALESCE(SUM(COALESCE(fact_sales.returns_qty, 0)), 0) AS returns_qty,
                COALESCE(SUM(CASE WHEN ({completed_condition}) THEN fact_sales.cogs_sum * fact_sales.qty ELSE 0 END), 0) AS cogs,
                COALESCE(SUM(CASE WHEN ({completed_condition}) THEN fact_sales.commission_sum ELSE 0 END), 0) AS commission,
                COALESCE(SUM(CASE WHEN ({completed_condition}) THEN fact_sales.logistics_sum ELSE 0 END), 0) AS logistics
            """
        else:
            extra_select = ""
        
        # Build query - агрегируем по d = date_created::date
        query = text(f"""
            SELECT 
                fact_sales.date_created::date AS day,
                COALESCE(SUM(CASE WHEN ({completed_condition}) THEN fact_sales.revenue_sum ELSE 0 END), 0) AS revenue,
                {orders_agg_sql} AS orders,
                COALESCE(SUM(CASE WHEN ({completed_condition}) THEN fact_sales.qty ELSE 0 END), 0) AS completed_qty
                {extra_select}
            FROM {qname("fact_sales")} fact_sales
            WHERE fact_sales.user_id = CAST(:user_id AS uuid)
                {shop_condition}
                {product_id_condition}
                {date_from_condition}
                AND fact_sales.date_created < CAST(:date_to AS date) + INTERVAL '1 day'
            GROUP BY fact_sales.date_created::date
            ORDER BY day ASC
        """)
        
        result = db.execute(query, params)
        rows = result.fetchall()
        logger.info(f"get_revenue_daily: found {len(rows)} points, period_range={period_range_dict}")
        
        # Extract date, revenue, orders, averageCheck; при product_id — returns, profit
        points = []
        for row in rows:
            try:
                day = row[0]
                date_str = day.isoformat() if hasattr(day, 'isoformat') else str(day)
                revenue = float(row[1]) if row[1] is not None else 0.0
                orders = float(row[2]) if row[2] is not None else 0.0
                completed_qty = float(row[3]) if row[3] is not None else 0.0
                average_check = (revenue / completed_qty) if completed_qty > 0 else 0.0
                returns_val = None
                profit_val = None
                if has_product_filter and len(row) >= 8:
                    returns_val = float(row[4]) if row[4] is not None else 0.0
                    cogs = float(row[5]) if row[5] is not None else 0.0
                    commission = float(row[6]) if row[6] is not None else 0.0
                    logistics = float(row[7]) if row[7] is not None else 0.0
                    profit_val = revenue - cogs - commission - logistics - (revenue * 0.01)
                points.append(RevenuePoint(
                    date=date_str,
                    revenue=revenue,
                    orders=orders,
                    averageCheck=average_check,
                    returns=returns_val,
                    profit=profit_val
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
            filters=RevenueFilters(shop_id=shop_id, shop=shop, product_id=product_id)
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
    date_from: Optional[str] = Query(default=None, description="Start date YYYY-MM-DD (overrides period when date_to also set)"),
    date_to: Optional[str] = Query(default=None, description="End date YYYY-MM-DD"),
    shop_id: Optional[str] = Query(default=None, description="Shop UUID"),
    shop: Optional[str] = Query(default=None, description="Shop name (string) for seller-storage filtering by barcode"),
    db: Session = Depends(get_db)
):
    """Get daily UZUM services chart data: storage, ads, fines from fact_expenses;
    commission, logistics from fact_sales (filterable by shop via barcode_norm).
    date_from/date_to (both set) override period; filter by date_written_off / date_created.
    """
    date_from_iso, date_to_iso, date_from, date_to_date, period_code, period_range_dict = resolve_date_range(
        date_from, date_to, period, db, user_id
    )
    shop_norm = normalize_shop(shop)

    # For period=all (or custom with no date_from), use MIN(date_written_off) or fallback
    if date_from is None:
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

    logger.info(f"get_uzum_services_daily: user_id={user_id}, period={period_code}, shop={shop}, shop_norm={shop_norm}, date_from={date_from_iso}, date_to={date_to_iso}")
    
    try:
        params_expenses = {
            "user_id": str(user_id),
            "date_from": date_from_iso,
            "date_to": date_to_iso
        }
        
        # 1) Expenses (expenses-report): storage, ads, fines — те же формулы, что в KPI Summary (по дням)
        # Реклама: SUM(Стоимость) Маркетинг+Оплата минус Маркетинг+Возврат
        # Хранение: SUM(Стоимость) Источник='Склад' и Тип операции='Оплата' минус Источник='Склад' и Тип операции='Возврат'
        # Штрафы: SUM(Сумма) Услуга LIKE '%Штраф%' и Оплата минус Возврат
        query_expenses = text(f"""
            SELECT 
                date_written_off::date AS day,
                COALESCE(SUM(
                    CASE
                        WHEN upper(trim(COALESCE(source, ''))) = 'СКЛАД' AND upper(trim(COALESCE(operation_type, ''))) = 'ОПЛАТА' THEN COALESCE(cost_sum, 0)
                        WHEN upper(trim(COALESCE(source, ''))) = 'СКЛАД' AND upper(trim(COALESCE(operation_type, ''))) = 'ВОЗВРАТ' THEN -COALESCE(cost_sum, 0)
                        ELSE 0
                    END
                ), 0) AS storage,
                COALESCE(SUM(
                    CASE
                        WHEN upper(trim(COALESCE(source, ''))) = 'МАРКЕТИНГ' AND upper(trim(COALESCE(operation_type, ''))) = 'ОПЛАТА' THEN COALESCE(cost_sum, 0)
                        WHEN upper(trim(COALESCE(source, ''))) = 'МАРКЕТИНГ' AND upper(trim(COALESCE(operation_type, ''))) = 'ВОЗВРАТ' THEN -COALESCE(cost_sum, 0)
                        ELSE 0
                    END
                ), 0) AS ads,
                COALESCE(SUM(
                    CASE
                        WHEN upper(COALESCE(service, '')) LIKE '%ШТРАФ%' AND upper(trim(COALESCE(operation_type, ''))) = 'ОПЛАТА' THEN COALESCE(amount_sum, 0)
                        WHEN upper(COALESCE(service, '')) LIKE '%ШТРАФ%' AND upper(trim(COALESCE(operation_type, ''))) = 'ВОЗВРАТ' THEN -COALESCE(amount_sum, 0)
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


def _parse_turnover(data: dict) -> Optional[float]:
    """Из data (jsonb) извлечь оборачиваемость; ключи: Оборачиваемость, дней / Оборачиваемость."""
    if not data:
        return None
    raw = data.get("Оборачиваемость, дней") or data.get("Оборачиваемость")
    if raw is None:
        return None
    try:
        if isinstance(raw, (int, float)):
            return float(raw)
        s = str(raw).strip().replace(",", ".")
        return float(s) if s else None
    except (TypeError, ValueError):
        return None


def _str_val(v) -> Optional[str]:
    if v is None:
        return None
    return str(v).strip() or None


@router.get("/charts/shipment-recommendations", response_model=ShipmentRecommendationsResponse)
async def get_shipment_recommendations(
    user_id: UUID = Depends(require_user),
    shop: Optional[str] = Query(default=None, description="Shop name (seller-storage) — фильтр по магазину через fact_storage_snapshot по баркодам"),
    db: Session = Depends(get_db)
):
    """Рекомендации по отгрузке: данные из left-out-report_old (Оборачиваемость < 60).
    Товар=Наименование, Артикул=SKU, Штрихкод, На складе=Общий остаток, Продаж в день=Среднесуточные продажи,
    Рекомендуемое кол-во='-', Запланировано к отгрузке=К отправке.
    При shop: только строки, чей баркод есть в fact_storage_snapshot для выбранного магазина.
    """
    try:
        shop_norm = normalize_shop(shop)
        params_batch = {"user_id": str(user_id)}
        shop_filter_sql = ""
        if shop_norm:
            params_batch["shop_norm"] = shop_norm
            shop_filter_sql = "\n              " + storage_barcode_filter_sql(
                "sl", prefix_and=True, outer_barcode_norm_expr=barcode_norm_sql("sl.barcode_raw")
            )

        # Последний батч: без shop — из fact_leftout_old_snapshot; с shop — из stg_leftout_old с фильтром по баркодам магазина
        if not shop_norm:
            batch_query = text(f"""
                SELECT upload_batch_id
                FROM {qname("fact_leftout_old_snapshot")}
                WHERE user_id = CAST(:user_id AS uuid)
                ORDER BY loaded_at DESC NULLS LAST
                LIMIT 1
            """)
        else:
            batch_query = text(f"""
                SELECT sl.upload_batch_id
                FROM {qname("stg_leftout_old")} sl
                WHERE sl.user_id = CAST(:user_id AS uuid)
                {shop_filter_sql}
                ORDER BY sl.upload_batch_id DESC NULLS LAST
                LIMIT 1
            """)
        batch_result = db.execute(batch_query, params_batch)
        batch_row = batch_result.fetchone()
        if not batch_row or not batch_row[0]:
            return ShipmentRecommendationsResponse(items=[])

        batch_id = str(batch_row[0])
        params_stg = {"user_id": str(user_id), "batch_id": batch_id}
        if shop_norm:
            params_stg["shop_norm"] = shop_norm
        stg_query = text(f"""
            SELECT sl.data, sl.barcode_raw, sl.in_sale_raw
            FROM {qname("stg_leftout_old")} sl
            WHERE sl.user_id = CAST(:user_id AS uuid)
              AND sl.upload_batch_id = CAST(:batch_id AS uuid)
            {shop_filter_sql}
        """)
        stg_result = db.execute(stg_query, params_stg)
        rows = stg_result.fetchall()

        items: list[ShipmentRecommendationItem] = []
        for row in rows:
            data = row[0]  # jsonb -> dict
            if not isinstance(data, dict):
                continue
            turnover = _parse_turnover(data)
            if turnover is None or turnover >= 60:
                continue
            barcode_raw = _str_val(row[1]) if len(row) > 1 else None
            in_sale_raw = _str_val(row[2]) if len(row) > 2 else None
            product_name = _str_val(data.get("Наименование") or data.get("Название товара"))
            sku = _str_val(data.get("SKU"))
            barcode = _str_val(data.get("Штрихкод")) or barcode_raw
            stock = _str_val(data.get("Общий остаток") or data.get("В продаже")) or in_sale_raw
            sales_per_day = _str_val(data.get("Среднесуточные продажи"))
            to_ship = _str_val(data.get("К отправке"))
            items.append(ShipmentRecommendationItem(
                product_name=product_name,
                sku=sku,
                barcode=barcode,
                stock=stock,
                sales_per_day=sales_per_day,
                recommended_qty="-",
                to_ship=to_ship,
                turnover=turnover,
            ))
        return ShipmentRecommendationsResponse(items=items)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_shipment_recommendations: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


def _parse_num(v) -> Optional[float]:
    """Parse number from data cell (int/float/string with comma)."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        s = str(v).strip().replace(",", ".")
        return float(s) if s else None
    except (TypeError, ValueError):
        return None


def _parse_int(v) -> Optional[int]:
    """Parse integer (e.g. В продаже, Остаток)."""
    n = _parse_num(v)
    return int(n) if n is not None and not (isinstance(n, float) and n != int(n)) else (int(n) if n is not None else None)


@router.get("/charts/products-table", response_model=ProductsTableResponse)
async def get_products_table(
    user_id: UUID = Depends(require_user),
    shop: Optional[str] = Query(default=None, description="Shop name (seller-storage) — filter by barcode set"),
    date_from: Optional[str] = Query(default=None, description="Start date YYYY-MM-DD (filters by fact_sales.date_created)"),
    date_to: Optional[str] = Query(default=None, description="End date YYYY-MM-DD (filters by fact_sales.date_created)"),
    db: Session = Depends(get_db)
):
    """
    Таблица товаров: три источника связаны по штрихкоду (barcode_norm):
    - left-out-report_old (stg_leftout_old / fact_leftout_old_snapshot) — база строк, Наименование, Артикул, Цена, Остаток, Оборачиваемость и т.д.
    - sells_report (fact_sales) — Продажи, Возвраты, Выручка, Себестоимость, Комиссия, Логистика
    - seller-storage (fact_storage_snapshot) — Габаритная группа, Магазин
    Связь по штрихкоду: barcode_norm = нормализованный штрихкод (пробелы убраны).
    
    Фильтрация по датам:
    - Основные метрики (продажи, выручка, прибыль и т.д.) фильтруются по date_from/date_to (по колонке date_created из fact_sales).
    - Если date_from и date_to не указаны, берутся все данные.
    - ABC анализ (ABC заказ, ABC прибыль, ABC выручка) всегда считается за последние 30 дней от последней даты в выгрузке и НЕ зависит от фильтров date_from/date_to.
    """
    try:
        import math
        # Определяем диапазон дат для основных метрик
        date_from_dt = None
        date_to_dt = None
        date_from_iso = None
        date_to_iso = None
        
        if date_from and date_to:
            try:
                date_from_dt = datetime.fromisoformat(date_from.strip()).date()
                date_to_dt = datetime.fromisoformat(date_to.strip()).date()
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date_from or date_to format (use YYYY-MM-DD).",
                )
            if date_from_dt > date_to_dt:
                raise HTTPException(
                    status_code=400,
                    detail="date_from must be less than or equal to date_to.",
                )
            date_from_iso = date_from_dt.isoformat()
            date_to_iso = date_to_dt.isoformat()
        
        # Период для ABC анализа: всегда последние 30 дней от последней даты в выгрузке (date_created из fact_sales).
        # ABC анализ не зависит от фильтров date_from/date_to - всегда используется период от последней даты минус 30 дней.
        data_end_date = get_data_end_date(db, user_id)
        abc_date_to_iso = data_end_date.isoformat()
        abc_date_from_iso = (data_end_date - timedelta(days=29)).isoformat()

        shop_norm = normalize_shop(shop)
        params_batch = {"user_id": str(user_id)}
        shop_filter_sql = ""
        if shop_norm:
            params_batch["shop_norm"] = shop_norm
            shop_filter_sql = "\n              " + storage_barcode_filter_sql(
                "sl", prefix_and=True, outer_barcode_norm_expr=barcode_norm_sql("sl.barcode_raw")
            )
        # Latest batch from stg_leftout_old (with optional shop filter by barcode set)
        batch_query = text(f"""
            SELECT sl.upload_batch_id FROM {qname("stg_leftout_old")} sl
            WHERE sl.user_id = CAST(:user_id AS uuid)
            {shop_filter_sql}
            ORDER BY sl.upload_batch_id DESC NULLS LAST
            LIMIT 1
        """)
        batch_result = db.execute(batch_query, params_batch)
        batch_row = batch_result.fetchone()
        if not batch_row or not batch_row[0]:
            return ProductsTableResponse(items=[])

        batch_id = str(batch_row[0])
        params_stg = {"user_id": str(user_id), "batch_id": batch_id}
        if shop_norm:
            params_stg["shop_norm"] = shop_norm
        stg_query = text(f"""
            SELECT sl.data, sl.barcode_raw, sl.in_sale_raw,
                   NULLIF(trim(regexp_replace(COALESCE(sl.barcode_raw, ''), '\\s+', '', 'g')), '') AS barcode_norm
            FROM {qname("stg_leftout_old")} sl
            WHERE sl.user_id = CAST(:user_id AS uuid)
              AND sl.upload_batch_id = CAST(:batch_id AS uuid)
            {shop_filter_sql if shop_norm else ""}
        """)
        stg_result = db.execute(stg_query, params_stg)
        stg_rows = stg_result.fetchall()

        # Связь по штрихкоду: left-out-report_old (строки выше) + seller-storage + sells_report по barcode_norm

        # Seller-storage: Габаритная группа и Магазин по barcode_norm (файл seller-storage = fact_storage_snapshot)
        storage_query = text(f"""
            SELECT
                COALESCE(fss.barcode_norm, NULLIF(trim(regexp_replace(COALESCE(fss.barcode, ''), '\\s+', '', 'g')), '')) AS barcode_norm,
                MAX(NULLIF(trim(fss.size_group), '')) AS size_group,
                MAX(NULLIF(trim(fss.shop_raw), '')) AS shop
            FROM {qname("fact_storage_snapshot")} fss
            WHERE fss.user_id = CAST(:user_id AS uuid)
              AND (fss.barcode_norm IS NOT NULL OR fss.barcode IS NOT NULL)
            GROUP BY fss.user_id, COALESCE(fss.barcode_norm, NULLIF(trim(regexp_replace(COALESCE(fss.barcode, ''), '\\s+', '', 'g')), ''))
        """)
        storage_result = db.execute(storage_query, {"user_id": str(user_id)})
        storage_by_barcode: dict = {}
        for row in storage_result.fetchall():
            bn = (row[0] or "").strip() if row[0] else ""
            if bn:
                sg = _str_val(row[1])
                if sg and "неопределен" in (sg or "").lower():
                    sg = "-"
                storage_by_barcode[bn] = {
                    "size_group": sg or "-",
                    "shop": _str_val(row[2]),
                }

        # Sells_report: агрегаты по barcode_norm с фильтрацией по датам (date_from/date_to).
        # Заказы (sales_qty) = файл sells_report из колонки Количество (qty) — суммирование без фильтрации по статусам.
        # Себестоимость/Выручка/Комиссия/Логистика — только со статусом «Завершен».
        # Если date_from и date_to не указаны, берутся все данные.
        
        # Формируем условие фильтрации по датам
        date_filter_sql = ""
        sales_params = {"user_id": str(user_id)}
        if date_from_dt and date_to_dt:
            date_filter_sql = """
              AND fs.date_created >= CAST(:date_from AS date)
              AND fs.date_created < CAST(:date_to AS date) + INTERVAL '1 day'
            """
            sales_params["date_from"] = date_from_iso
            sales_params["date_to"] = date_to_iso
        
        sales_query = text(f"""
            SELECT
                fs.barcode_norm,
                SUM(COALESCE(fs.qty, 0))::int AS sales_qty,
                SUM(COALESCE(fs.returns_qty, 0))::int AS returns_qty,
                SUM(CASE WHEN {_STATUS_COMPLETED_SQL} THEN COALESCE(fs.revenue_sum, 0) ELSE 0 END)::double precision AS revenue,
                SUM(CASE WHEN {_STATUS_COMPLETED_SQL} THEN COALESCE(fs.cogs_sum * fs.qty, 0) ELSE 0 END)::double precision AS cogs,
                SUM(CASE WHEN {_STATUS_COMPLETED_SQL} THEN COALESCE(fs.commission_sum, 0) ELSE 0 END)::double precision AS commission,
                SUM(CASE WHEN {_STATUS_COMPLETED_SQL} THEN COALESCE(fs.logistics_sum, 0) ELSE 0 END)::double precision AS logistics
            FROM {qname("fact_sales")} fs
            WHERE fs.user_id = CAST(:user_id AS uuid)
              AND fs.barcode_norm IS NOT NULL
            {date_filter_sql}
            GROUP BY fs.barcode_norm
        """)
        sales_result = db.execute(sales_query, sales_params)
        sales_by_barcode: dict = {}
        for row in sales_result.fetchall():
            bn = (row[0] or "").strip() if row[0] else ""
            if bn:
                revenue_val = float(row[3] or 0)
                cogs_total_val = float(row[4] or 0)
                commission_val = float(row[5] or 0)
                logistics_val = float(row[6] or 0)
                # Прибыль по тому же принципу, что и в блоке Финансы:
                # profit = revenue - (cogs + commission + logistics + налог 1% с выручки)
                profit_val = (
                    revenue_val
                    - cogs_total_val
                    - commission_val
                    - logistics_val
                    - (revenue_val * 0.01)
                )
                sales_by_barcode[bn] = {
                    "sales_qty": int(row[1] or 0),
                    "returns_qty": int(row[2] or 0),
                    "revenue": revenue_val,
                    "cogs_total": cogs_total_val,
                    "commission": commission_val,
                    "logistics": logistics_val,
                    "profit": profit_val,
                }

        # Цена и Себестоимость для таблицы: по последней дате продаж для каждого штрихкода в выбранном периоде.
        # Цена = revenue_sum / qty, Себестоимость = cogs_sum / qty на последнюю дату (только завершённые заказы).
        last_price_cogs_by_barcode: dict[str, dict[str, float]] = {}
        
        # Формируем условие фильтрации по датам для запроса цены и себестоимости
        last_unit_date_filter_sql = ""
        last_unit_params = {"user_id": str(user_id)}
        if date_from_dt and date_to_dt:
            last_unit_date_filter_sql = """
              AND fs.date_created >= CAST(:date_from AS date)
              AND fs.date_created < CAST(:date_to AS date) + INTERVAL '1 day'
            """
            last_unit_params["date_from"] = date_from_iso
            last_unit_params["date_to"] = date_to_iso
        
        last_unit_query = text(f"""
            WITH last_dates AS (
                SELECT
                    fs.barcode_norm,
                    MAX(fs.date_created::date) AS last_date
                FROM {qname("fact_sales")} fs
                WHERE fs.user_id = CAST(:user_id AS uuid)
                  AND fs.barcode_norm IS NOT NULL
                  AND {_STATUS_COMPLETED_SQL}
                  {last_unit_date_filter_sql}
                GROUP BY fs.barcode_norm
            ),
            last_rows AS (
                SELECT
                    fs.barcode_norm,
                    fs.revenue_sum,
                    fs.cogs_sum,
                    fs.qty
                FROM {qname("fact_sales")} fs
                JOIN last_dates ld
                  ON ld.barcode_norm = fs.barcode_norm
                 AND fs.date_created::date = ld.last_date
                WHERE fs.user_id = CAST(:user_id AS uuid)
                  AND {_STATUS_COMPLETED_SQL}
            )
            SELECT
                barcode_norm,
                CASE WHEN COALESCE(SUM(qty), 0) > 0
                     THEN SUM(COALESCE(revenue_sum, 0)) / NULLIF(SUM(qty), 0)
                     ELSE 0
                END AS unit_price,
                CASE WHEN COALESCE(SUM(qty), 0) > 0
                     THEN SUM(COALESCE(cogs_sum, 0)) / NULLIF(SUM(qty), 0)
                     ELSE 0
                END AS unit_cogs
            FROM last_rows
            GROUP BY barcode_norm
        """)
        last_unit_result = db.execute(last_unit_query, last_unit_params)
        for row in last_unit_result.fetchall():
            bn = (row[0] or "").strip() if row[0] else ""
            if not bn:
                continue
            unit_price = float(row[1] or 0)
            unit_cogs = float(row[2] or 0)
            last_price_cogs_by_barcode[bn] = {
                "price": unit_price,
                "cogs": unit_cogs,
            }

        # ABC-заказы по количеству (sales_qty) за последние 30 дней:
        # A — первые ~80% суммарного qty, B — до 95%, C — остальные.
        # Для ABC анализа используем отдельный запрос с ограничением по датам.
        # Заказы (sales_qty) = файл sells_report из колонки Количество (qty) — суммирование без фильтрации по статусам.
        # ABC анализ всегда считается за последние 30 дней от последней даты в выгрузке (независимо от фильтров date_from/date_to).
        abc_sales_query = text(f"""
            SELECT
                fs.barcode_norm,
                SUM(COALESCE(fs.qty, 0))::int AS sales_qty,
                SUM(CASE WHEN {_STATUS_COMPLETED_SQL} THEN COALESCE(fs.revenue_sum, 0) ELSE 0 END)::double precision AS revenue,
                SUM(CASE WHEN {_STATUS_COMPLETED_SQL} THEN COALESCE(fs.cogs_sum * fs.qty, 0) ELSE 0 END)::double precision AS cogs,
                SUM(CASE WHEN {_STATUS_COMPLETED_SQL} THEN COALESCE(fs.commission_sum, 0) ELSE 0 END)::double precision AS commission,
                SUM(CASE WHEN {_STATUS_COMPLETED_SQL} THEN COALESCE(fs.logistics_sum, 0) ELSE 0 END)::double precision AS logistics
            FROM {qname("fact_sales")} fs
            WHERE fs.user_id = CAST(:user_id AS uuid)
              AND fs.barcode_norm IS NOT NULL
              AND fs.date_created >= CAST(:abc_date_from AS date)
              AND fs.date_created < CAST(:abc_date_to AS date) + INTERVAL '1 day'
            GROUP BY fs.barcode_norm
        """)
        abc_sales_result = db.execute(abc_sales_query, {
            "user_id": str(user_id), 
            "abc_date_from": abc_date_from_iso, 
            "abc_date_to": abc_date_to_iso
        })
        abc_sales_by_barcode: dict = {}
        for row in abc_sales_result.fetchall():
            bn = (row[0] or "").strip() if row[0] else ""
            if bn:
                revenue_val = float(row[2] or 0)
                cogs_total_val = float(row[3] or 0)
                commission_val = float(row[4] or 0)
                logistics_val = float(row[5] or 0)
                profit_val = (
                    revenue_val
                    - cogs_total_val
                    - commission_val
                    - logistics_val
                    - (revenue_val * 0.01)
                )
                abc_sales_by_barcode[bn] = {
                    "sales_qty": int(row[1] or 0),
                    "revenue": revenue_val,
                    "profit": profit_val,
                }
        
        abc_orders_by_barcode: dict[str, str] = {}
        total_sales_qty = sum(max(data["sales_qty"], 0) for data in abc_sales_by_barcode.values())
        if total_sales_qty > 0:
            # Сортируем SKU по qty по убыванию
            sorted_items = sorted(
                abc_sales_by_barcode.items(),
                key=lambda kv: kv[1]["sales_qty"],
                reverse=True,
            )
            cumulative = 0
            for bn, data in sorted_items:
                qty = max(data["sales_qty"], 0)
                if qty == 0:
                    # Нулевые заказы всегда пойдут в C
                    abc_orders_by_barcode[bn] = "C"
                    continue
                cumulative += qty
                share = cumulative / total_sales_qty * 100
                if share <= 80:
                    abc_orders_by_barcode[bn] = "A"
                elif share <= 95:
                    abc_orders_by_barcode[bn] = "B"
                else:
                    abc_orders_by_barcode[bn] = "C"

        # ABC-прибыль по накопленной прибыли (profit) за последние 30 дней:
        # A — первые ~80% суммарной прибыли, B — до 95%, C — остальные.
        abc_profit_by_barcode: dict[str, str] = {}
        # Берём только положительную прибыль для расчёта долей; нулевая/отрицательная = класс C.
        total_profit = sum(max(data["profit"], 0.0) for data in abc_sales_by_barcode.values())
        if total_profit > 0:
            sorted_by_profit = sorted(
                abc_sales_by_barcode.items(),
                key=lambda kv: kv[1]["profit"],
                reverse=True,
            )
            cumulative_profit = 0.0
            for bn, data in sorted_by_profit:
                profit_val = max(data["profit"], 0.0)
                if profit_val <= 0:
                    abc_profit_by_barcode[bn] = "C"
                    continue
                cumulative_profit += profit_val
                share_profit = cumulative_profit / total_profit * 100
                if share_profit <= 80:
                    abc_profit_by_barcode[bn] = "A"
                elif share_profit <= 95:
                    abc_profit_by_barcode[bn] = "B"
                else:
                    abc_profit_by_barcode[bn] = "C"

        # ABC-выручка по накопленной выручке (revenue) за последние 30 дней:
        # A — первые ~80% суммарной выручки, B — до 95%, C — остальные.
        abc_revenue_by_barcode: dict[str, str] = {}
        total_revenue = sum(max(data["revenue"], 0.0) for data in abc_sales_by_barcode.values())
        if total_revenue > 0:
            sorted_by_revenue = sorted(
                abc_sales_by_barcode.items(),
                key=lambda kv: kv[1]["revenue"],
                reverse=True,
            )
            cumulative_revenue = 0.0
            for bn, data in sorted_by_revenue:
                revenue_val = max(data["revenue"], 0.0)
                if revenue_val <= 0:
                    abc_revenue_by_barcode[bn] = "C"
                    continue
                cumulative_revenue += revenue_val
                share_revenue = cumulative_revenue / total_revenue * 100
                if share_revenue <= 80:
                    abc_revenue_by_barcode[bn] = "A"
                elif share_revenue <= 95:
                    abc_revenue_by_barcode[bn] = "B"
                else:
                    abc_revenue_by_barcode[bn] = "C"

        items: list[ProductsTableItem] = []
        for row in stg_rows:
            data = row[0]
            if not isinstance(data, dict):
                continue
            barcode_raw = _str_val(row[1])
            in_sale_raw = _str_val(row[2])
            barcode_norm = (row[3] or "").strip() if row[3] else ""
            if not barcode_norm and barcode_raw:
                barcode_norm = (barcode_raw or "").replace(" ", "").strip()

            product_id = _str_val(data.get("ID товара"))
            product_name = _str_val(data.get("Наименование") or data.get("Название товара"))
            sku = _str_val(data.get("SKU"))
            price = _parse_num(data.get("Стоимость продажи (сумы)"))
            turnover = _parse_turnover(data)
            stock = _parse_int(data.get("Общий остаток") or data.get("В продаже") or in_sale_raw)
            storage_cost = _parse_num(data.get("Стоимость хранения 1 дня, сум") or data.get("Стоимость хранения 1 дня"))
            barcode = _str_val(data.get("Штрихкод")) or barcode_raw

            # Габаритная группа и Магазин — только из seller-storage (fact_storage_snapshot), колонка Магазин = shop_raw
            shop = None
            size_group = "-"
            storage_row = storage_by_barcode.get(barcode_norm) if barcode_norm else None
            if storage_row:
                size_group = storage_row["size_group"]
                shop = storage_row["shop"]  # только из seller-storage, колонка Магазин

            sales_row = sales_by_barcode.get(barcode_norm) if barcode_norm else None
            if sales_row:
                sales_qty = sales_row["sales_qty"]
                returns_qty = sales_row["returns_qty"]
                revenue = sales_row["revenue"]
                # По умолчанию cogs_total — агрегированная себестоимость по всем завершённым заказам.
                cogs_total = sales_row["cogs_total"]
                commission = sales_row["commission"]
                logistics = sales_row["logistics"]
            else:
                sales_qty = returns_qty = 0
                revenue = cogs_total = commission = logistics = 0.0

            # Цена и Себестоимость для таблицы: используем значения от последней даты продаж, если есть.
            display_price = None
            display_cogs = None
            if barcode_norm:
                last_unit = last_price_cogs_by_barcode.get(barcode_norm)
                if last_unit:
                    display_price = last_unit["price"]
                    display_cogs = last_unit["cogs"]

            if display_price is None:
                # Fallback: старая логика (из left-out-report или по данным leftout_old)
                display_price = price
            if display_cogs is None:
                # Fallback: агрегированная себестоимость
                display_cogs = cogs_total

            # Прибыль по тому же принципу, что и для ABC-прибыли:
            profit = revenue - cogs_total - commission - logistics - (revenue * 0.01)

            items.append(ProductsTableItem(
                product_id=product_id,
                product_name=product_name,
                sku=sku,
                price=display_price,
                sales_qty=sales_qty,
                returns_qty=returns_qty,
                revenue=revenue,
                profit=profit,
                turnover=turnover,
                stock=stock,
                size_group=size_group or "-",
                cogs=display_cogs,
                cogs_total=cogs_total,
                commission=commission,
                logistics=logistics,
                abc_orders=abc_orders_by_barcode.get(barcode_norm),
                abc_profit=abc_profit_by_barcode.get(barcode_norm),
                abc_revenue=abc_revenue_by_barcode.get(barcode_norm),
                barcode=barcode,
                storage_cost_per_day=storage_cost,
                shop=shop,
            ))
        return ProductsTableResponse(items=items)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_products_table: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/products/{product_id}/comment", response_model=ProductCommentResponse)
async def get_product_comment(
    product_id: str,
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get comment for a product by product_id."""
    try:
        # Проверяем, существует ли таблица
        check_table_query = text(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = :schema 
                AND table_name = 'product_comments'
            )
        """)
        table_exists = db.execute(check_table_query, {"schema": settings.DB_SCHEMA}).scalar()
        
        if not table_exists:
            # Если таблицы нет, возвращаем пустой комментарий
            return ProductCommentResponse(product_id=product_id, comment=None)
        
        query = text(f"""
            SELECT content
            FROM {qname("product_comments")}
            WHERE user_id = CAST(:user_id AS uuid)
              AND product_id = :product_id
            ORDER BY updated_at DESC
            LIMIT 1
        """)
        result = db.execute(query, {"user_id": str(user_id), "product_id": product_id})
        row = result.fetchone()
        comment = row[0] if row else None
        return ProductCommentResponse(product_id=product_id, comment=comment)
    except Exception as e:
        logger.error(f"Error in get_product_comment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/products/{product_id}/comment", response_model=ProductCommentResponse)
async def save_product_comment(
    product_id: str,
    request: ProductCommentRequest,
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Save or update comment for a product by product_id."""
    try:
        if request.product_id != product_id:
            raise HTTPException(status_code=400, detail="product_id mismatch")
        
        comment_text = request.comment.strip() if request.comment and request.comment.strip() else None
        comment_date = datetime.now().date().isoformat()
        
        # Проверяем, существует ли таблица, и создаем её, если нет
        try:
            check_table_query = text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = :schema 
                    AND table_name = 'product_comments'
                )
            """)
            table_exists = db.execute(check_table_query, {"schema": settings.DB_SCHEMA}).scalar()
            
            if not table_exists:
                # Создаем таблицу, если её нет
                create_table_query = text(f"""
                    CREATE TABLE {qname("product_comments")} (
                        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id uuid NOT NULL,
                        product_id text NOT NULL,
                        content text,
                        comment_date date NOT NULL,
                        created_at timestamptz NOT NULL DEFAULT now(),
                        updated_at timestamptz NOT NULL DEFAULT now()
                    )
                """)
                db.execute(create_table_query)
                
                # Создаем индекс для быстрого поиска
                create_index_query = text(f"""
                    CREATE INDEX idx_product_comments_user_product 
                    ON {qname("product_comments")} (user_id, product_id)
                """)
                db.execute(create_index_query)
                db.commit()
                logger.info(f"Created table {qname('product_comments')}")
        except Exception as table_error:
            # Если таблица уже существует или другая ошибка, продолжаем
            logger.warning(f"Table check/create failed (may already exist): {table_error}")
            db.rollback()
        
        # Проверяем, существует ли комментарий
        check_query = text(f"""
            SELECT id FROM {qname("product_comments")}
            WHERE user_id = CAST(:user_id AS uuid)
              AND product_id = :product_id
            LIMIT 1
        """)
        check_result = db.execute(check_query, {"user_id": str(user_id), "product_id": product_id})
        existing = check_result.fetchone()
        
        # Если комментарий пустой и записи нет, просто возвращаем успех
        if not comment_text and not existing:
            return ProductCommentResponse(product_id=product_id, comment=None)
        
        if existing:
            # Обновляем существующий комментарий
            if comment_text:
                update_query = text(f"""
                    UPDATE {qname("product_comments")}
                    SET content = :content,
                        comment_date = CAST(:comment_date AS date),
                        updated_at = now()
                    WHERE id = CAST(:id AS uuid)
                      AND user_id = CAST(:user_id AS uuid)
                """)
                db.execute(update_query, {
                    "id": existing[0],
                    "user_id": str(user_id),
                    "content": comment_text,
                    "comment_date": comment_date
                })
            else:
                # Удаляем комментарий, если он пустой
                delete_query = text(f"""
                    DELETE FROM {qname("product_comments")}
                    WHERE id = CAST(:id AS uuid)
                      AND user_id = CAST(:user_id AS uuid)
                """)
                db.execute(delete_query, {"id": existing[0], "user_id": str(user_id)})
        else:
            # Создаем новый комментарий
            if comment_text:
                insert_query = text(f"""
                    INSERT INTO {qname("product_comments")} (user_id, product_id, content, comment_date)
                    VALUES (CAST(:user_id AS uuid), :product_id, :content, CAST(:comment_date AS date))
                """)
                db.execute(insert_query, {
                    "user_id": str(user_id),
                    "product_id": product_id,
                    "content": comment_text,
                    "comment_date": comment_date
                })
        
        db.commit()
        return ProductCommentResponse(product_id=product_id, comment=comment_text)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error in save_product_comment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/charts/orders-sales-daily", response_model=OrdersSalesDailyResponse)
async def get_orders_sales_daily(
    user_id: UUID = Depends(require_user),
    period: str = Query(default="30d", description="Period: 7d, 30d, 90d, or all"),
    date_from: Optional[str] = Query(default=None, description="Start date YYYY-MM-DD (overrides period when date_to also set)"),
    date_to: Optional[str] = Query(default=None, description="End date YYYY-MM-DD"),
    shop_id: Optional[str] = Query(default=None, description="Shop UUID"),
    shop: Optional[str] = Query(default=None, description="Shop name (string) for seller-storage filtering by barcode"),
    group_by: str = Query(default="day", description="Grouping: day, week, or month"),
    db: Session = Depends(get_db)
):
    """Get orders and sales chart data grouped by time period (day/week/month).
    When shop (string) is set, filter by products in fact_storage_snapshot for that shop (barcode_norm).
    All metrics use the SAME formulas as /api/kpi/summary.
    date_from/date_to (both set) override period; filter by fact_sales.date_created.
    """
    date_from_iso, date_to_iso, date_from, date_to_date, period_code, period_range_dict = resolve_date_range(
        date_from, date_to, period, db, user_id
    )
    shop_norm = normalize_shop(shop)

    # For period=all (or custom with no date_from), use MIN(date_created) or fallback
    if date_from is None:
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
    date_from: Optional[str] = Query(default=None, description="Start date YYYY-MM-DD (overrides period when date_to also set)"),
    date_to: Optional[str] = Query(default=None, description="End date YYYY-MM-DD"),
    shop_id: Optional[str] = Query(default=None, description="Shop UUID"),
    shop: Optional[str] = Query(default=None, description="Shop name (string) for seller-storage filtering by barcode"),
    granularity: str = Query(default="day", description="Aggregation: day, week, or month (week = Monday-based)"),
    db: Session = Depends(get_db)
):
    """Get daily summary table (По дням — Данные по дням). Same formulas as Сводка.
    granularity=day|week|month: aggregate by date bucket (week = Monday start). Same metrics, SUM per bucket.
    Filters: date_from/date_to (or period), shop (seller-storage Магазин → barcode filter).
    date_from/date_to (both set) override period; filter by fact_sales.date_created / fact_expenses.date_written_off.
    """
    date_from_iso, date_to_iso, date_from, date_to_date, period_code, period_range_dict = resolve_date_range(
        date_from, date_to, period, db, user_id
    )
    gran = (granularity or "day").strip().lower()
    if gran not in ("day", "week", "month"):
        gran = "day"

    if date_from is None:
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

    # УСЛУГИ UZUM: Хранение/Реклама/Штрафы из fact_expenses (тот же источник и формулы, что в Сводке)
    try:
        if gran == "day":
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
                                WHEN upper(trim(COALESCE(fe.source, ''))) = 'СКЛАД' AND upper(trim(COALESCE(fe.operation_type, ''))) = 'ОПЛАТА' THEN COALESCE(fe.cost_sum, 0)
                                WHEN upper(trim(COALESCE(fe.source, ''))) = 'СКЛАД' AND upper(trim(COALESCE(fe.operation_type, ''))) = 'ВОЗВРАТ' THEN -COALESCE(fe.cost_sum, 0)
                                ELSE 0
                            END
                        ), 0) AS storage,
                        COALESCE(SUM(
                            CASE
                                WHEN upper(trim(COALESCE(fe.source, ''))) = 'МАРКЕТИНГ' AND upper(trim(COALESCE(fe.operation_type, ''))) = 'ОПЛАТА' THEN COALESCE(fe.cost_sum, 0)
                                WHEN upper(trim(COALESCE(fe.source, ''))) = 'МАРКЕТИНГ' AND upper(trim(COALESCE(fe.operation_type, ''))) = 'ВОЗВРАТ' THEN -COALESCE(fe.cost_sum, 0)
                                ELSE 0
                            END
                        ), 0) AS ads,
                        COALESCE(SUM(
                            CASE
                                WHEN upper(COALESCE(fe.service, '')) LIKE '%ШТРАФ%' AND upper(trim(COALESCE(fe.operation_type, ''))) = 'ОПЛАТА' THEN COALESCE(fe.amount_sum, 0)
                                WHEN upper(COALESCE(fe.service, '')) LIKE '%ШТРАФ%' AND upper(trim(COALESCE(fe.operation_type, ''))) = 'ВОЗВРАТ' THEN -COALESCE(fe.amount_sum, 0)
                                ELSE 0
                            END
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
        else:
            # week or month: bucket = date_trunc(gran, date)::date (Postgres week = Monday)
            trunc_part = "week" if gran == "week" else "month"
            interval_step = "1 week" if gran == "week" else "1 month"
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
                                WHEN upper(trim(COALESCE(fe.source, ''))) = 'СКЛАД' AND upper(trim(COALESCE(fe.operation_type, ''))) = 'ОПЛАТА' THEN COALESCE(fe.cost_sum, 0)
                                WHEN upper(trim(COALESCE(fe.source, ''))) = 'СКЛАД' AND upper(trim(COALESCE(fe.operation_type, ''))) = 'ВОЗВРАТ' THEN -COALESCE(fe.cost_sum, 0)
                                ELSE 0
                            END
                        ), 0) AS storage,
                        COALESCE(SUM(
                            CASE
                                WHEN upper(trim(COALESCE(fe.source, ''))) = 'МАРКЕТИНГ' AND upper(trim(COALESCE(fe.operation_type, ''))) = 'ОПЛАТА' THEN COALESCE(fe.cost_sum, 0)
                                WHEN upper(trim(COALESCE(fe.source, ''))) = 'МАРКЕТИНГ' AND upper(trim(COALESCE(fe.operation_type, ''))) = 'ВОЗВРАТ' THEN -COALESCE(fe.cost_sum, 0)
                                ELSE 0
                            END
                        ), 0) AS ads,
                        COALESCE(SUM(
                            CASE
                                WHEN upper(COALESCE(fe.service, '')) LIKE '%ШТРАФ%' AND upper(trim(COALESCE(fe.operation_type, ''))) = 'ОПЛАТА' THEN COALESCE(fe.amount_sum, 0)
                                WHEN upper(COALESCE(fe.service, '')) LIKE '%ШТРАФ%' AND upper(trim(COALESCE(fe.operation_type, ''))) = 'ВОЗВРАТ' THEN -COALESCE(fe.amount_sum, 0)
                                ELSE 0
                            END
                        ), 0) AS penalties
                    FROM {qname('fact_expenses')} fe
                    WHERE fe.user_id = CAST(:user_id AS uuid)
                        AND fe.date_written_off >= CAST(:date_from AS date)
                        AND fe.date_written_off < CAST(:date_to AS date) + INTERVAL '1 day'
                    GROUP BY fe.date_written_off::date
                ),
                daily_joined AS (
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
                ),
                aggregated AS (
                    SELECT
                        date_trunc('{trunc_part}', daily_joined.date)::date AS bucket,
                        SUM(orders) AS orders,
                        SUM(buys) AS buys,
                        SUM(returns) AS returns,
                        SUM(revenue) AS revenue,
                        SUM(commission) AS commission,
                        SUM(logistics) AS logistics,
                        SUM(storage) AS storage,
                        SUM(ads) AS ads,
                        SUM(penalties) AS penalties,
                        SUM(cogs) AS cogs,
                        SUM(taxes) AS taxes,
                        SUM(profit) AS profit
                    FROM daily_joined
                    GROUP BY date_trunc('{trunc_part}', daily_joined.date)::date
                ),
                buckets AS (
                    SELECT generate_series(
                        date_trunc('{trunc_part}', CAST(:date_from AS date))::date,
                        CAST(:date_to AS date),
                        INTERVAL '{interval_step}'
                    )::date AS bucket
                )
                SELECT
                    b.bucket AS date,
                    COALESCE(a.orders, 0) AS orders,
                    COALESCE(a.buys, 0) AS buys,
                    COALESCE(a.returns, 0) AS returns,
                    COALESCE(a.revenue, 0) AS revenue,
                    COALESCE(a.commission, 0) AS commission,
                    COALESCE(a.logistics, 0) AS logistics,
                    COALESCE(a.storage, 0) AS storage,
                    COALESCE(a.ads, 0) AS ads,
                    COALESCE(a.penalties, 0) AS penalties,
                    COALESCE(a.cogs, 0) AS cogs,
                    COALESCE(a.taxes, 0) AS taxes,
                    COALESCE(a.profit, 0) AS profit
                FROM buckets b
                LEFT JOIN aggregated a ON b.bucket = a.bucket
                ORDER BY b.bucket ASC
            """)
        result = db.execute(query, params)
        rows = result.fetchall()
        logger.info(f"get_daily_summary: found {len(rows)} points (granularity={gran}), period={period_code}, shop_norm={shop_norm}")

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
