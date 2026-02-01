from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta
import logging
from app.db import get_db, qname
from app.deps import require_user
from app.utils.statuses import get_status_sql_condition
from app.utils.barcode import barcode_norm_sql
from app.utils.metrics import get_status_conditions
from app.utils.shop_filter import normalize_shop, shop_filter_condition, storage_barcode_filter_sql, storage_barcode_filter_by_shop_id_sql
from app.settings import get_settings
from app.schemas import CumulativeRevenueResponse
from fastapi import Depends

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


def normalize_period(period: str) -> str:
    """Normalize period string to standard format: 7d, 30d, 90d, or all."""
    period_lower = period.lower().strip()
    
    if period_lower in ("7d", "week", "неделя"):
        return "7d"
    elif period_lower in ("30d", "30"):
        return "30d"
    elif period_lower in ("90d", "90"):
        return "90d"
    elif period_lower in ("all", "все", "все данные"):
        return "all"
    else:
        # Default to 30d if unknown
        return "30d"


def get_data_end_date(db: Session, user_id: UUID) -> datetime.date:
    """
    Get the maximum date only from sales report (fact_sales.date_created) for the user.
    If there are no sales rows, fallback to CURRENT_DATE (today).
    shop_id is NOT considered (period is stable across shops).
    """
    q = text(f"""
        SELECT COALESCE(
            (SELECT MAX(date_created)::date
             FROM {qname("fact_sales")}
             WHERE user_id = CAST(:user_id AS uuid)),
            CURRENT_DATE
        ) AS data_end_date
    """)
    result = db.execute(q, {"user_id": str(user_id)})
    data_end_date = result.scalar()
    return data_end_date or datetime.now().date()


def period_range(period_code: str, data_end_date: datetime.date) -> dict:
    """
    Calculate date range for period code based on data_end_date.
    Returns: {code, date_from, date_to}
    - date_to = data_end_date (not CURRENT_DATE)
    - 7d: date_from = date_to - 6 days
    - 30d: date_from = date_to - 29 days
    - 90d: date_from = date_to - 89 days
    - all: date_from = None
    """
    date_to_iso = data_end_date.isoformat()
    
    if period_code == "all":
        date_from = None
    elif period_code == "7d":
        date_from = data_end_date - timedelta(days=6)
    elif period_code == "30d":
        date_from = data_end_date - timedelta(days=29)
    elif period_code == "90d":
        date_from = data_end_date - timedelta(days=89)
    else:
        # Fallback to 30d
        date_from = data_end_date - timedelta(days=29)
    
    return {
        "code": period_code,
        "date_from": date_from.isoformat() if date_from else None,
        "date_to": date_to_iso
    }


def resolve_date_range(
    date_from_param: Optional[str],
    date_to_param: Optional[str],
    period_param: str,
    db: Session,
    user_id: UUID,
):
    """
    Resolve date range from request: explicit date_from/date_to (priority) or period.
    Returns: (date_from_iso, date_to_iso, date_from_dt, date_to_dt, period_code, period_range_dict).
    Raises HTTPException 400 on invalid date_from/date_to.
    """
    date_from_iso = None
    date_to_iso = None
    date_from_dt = None
    date_to_dt = None
    period_code = "30d"
    period_range_dict = {"mode": "period", "date_from": None, "date_to": None, "period": period_code}

    if date_from_param and date_to_param:
        try:
            from_dt = datetime.fromisoformat(date_from_param.strip()).date()
            to_dt = datetime.fromisoformat(date_to_param.strip()).date()
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=400,
                detail="Invalid date_from or date_to format (use YYYY-MM-DD).",
            )
        if from_dt > to_dt:
            raise HTTPException(
                status_code=400,
                detail="date_from must be less than or equal to date_to.",
            )
        date_from_iso = from_dt.isoformat()
        date_to_iso = to_dt.isoformat()
        date_from_dt = from_dt
        date_to_dt = to_dt
        period_code = "custom"
        period_range_dict = {"mode": "custom", "date_from": date_from_iso, "date_to": date_to_iso, "period": period_code}
    else:
        period_code = normalize_period(period_param)
        data_end_date = get_data_end_date(db, user_id)
        pr = period_range(period_code, data_end_date)
        date_to_iso = pr["date_to"]
        date_from_iso = pr["date_from"]
        if date_to_iso is None:
            date_to_dt = datetime.now().date()
            date_to_iso = date_to_dt.isoformat()
        else:
            date_to_dt = datetime.fromisoformat(date_to_iso).date()
        date_from_dt = datetime.fromisoformat(date_from_iso).date() if date_from_iso else None
        period_range_dict = {"mode": "period", "date_from": date_from_iso, "date_to": date_to_iso, "period": period_code}

    return (date_from_iso, date_to_iso, date_from_dt, date_to_dt, period_code, period_range_dict)


@router.get("/kpi/summary")
def kpi_summary(
    period: str = "30d",
    date_from: Optional[str] = Query(default=None, description="Start date YYYY-MM-DD (overrides period when date_to also set)"),
    date_to: Optional[str] = Query(default=None, description="End date YYYY-MM-DD"),
    shop_id: Optional[str] = None,
    shop: Optional[str] = Query(default=None, description="Shop name (string) for seller-storage filtering"),
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Get KPI summary metrics.

    Filtering:
    - date_from, date_to: explicit range (from fact_sales.date_created). When both set, period is ignored.
    - shop_id (UUID): for sales/expenses (from dim_shop)
    - shop (string): for seller-storage metrics (from stg_storage.shop_raw)

    Exceptions (never filtered by dates):
    - Stock block: always latest snapshot.
    - cumulativeRevenue: always all-time, no shop (same as GET /kpi/cumulative-revenue).

    Test examples:
    - GET /api/kpi/summary?period=30d
    - GET /api/kpi/summary?date_from=2025-11-01&date_to=2025-11-30
    - GET /api/kpi/summary?period=30d&date_from=2025-11-01&date_to=2025-11-30  (dates take priority)
    """
    # 1) Единый расчёт диапазона дат: date_from/date_to (приоритет) или period. period_range_dict задаётся всегда.
    date_from_iso, date_to_iso, date_from_dt, date_to_dt, period_code, period_range_dict = resolve_date_range(
        date_from_param=date_from,
        date_to_param=date_to,
        period_param=period,
        db=db,
        user_id=user_id,
    )
    date_from = date_from_dt  # date object or None (used in SQL)
    date_to_date = date_to_dt

    # Validate shop_id if provided (only if shop is NOT provided)
    # Если передан shop (строка) - это для seller-storage, shop_id не валидируем как UUID
    if shop_id and not shop:
        try:
            UUID(shop_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid shop_id format (must be UUID). For seller-storage filtering use 'shop' parameter instead."
            )
    
    # Нормализуем shop для seller-storage фильтрации (единый helper)
    shop_norm = normalize_shop(shop)

    # Диагностика: убедиться, что KPI считаются по выбранным датам (не по period)
    logger.info(
        "kpi_summary dates: date_from=%s date_to=%s period_param=%s (all blocks use this range)",
        date_from_iso,
        date_to_iso,
        period,
    )
    logger.info(f"kpi_summary: user_id={user_id}, shop_id={shop_id}, shop={shop}, shop_norm={shop_norm}, period={period_code}, period_range={period_range_dict}")
    
    try:
        # Diagnostic: log current database and schema for troubleshooting search_path / barcode_norm issues
        try:
            diag_row = db.execute(text("SELECT current_database(), current_schema()")).fetchone()
            logger.info(f"kpi_summary: current_database={diag_row[0]}, current_schema={diag_row[1]}")
        except Exception as diag_err:
            logger.warning(f"kpi_summary: could not get schema diagnostic: {diag_err}")

        # Base parameters - ALWAYS includes user_id and date_to; shop_norm for storage filter
        params_base = {
            "user_id": str(user_id),
            "date_to": date_to_iso,
            "shop_id": shop_id,  # Can be None (UUID)
            "shop_norm": shop_norm,  # Can be None (seller-storage name, normalized)
        }
        
        # Sales shop filter: by storage barcodes (shop_norm) or by shop_id (UUID) — единый helper
        sales_shop_filter, sales_shop_params = shop_filter_condition(shop, shop_id, outer_table_alias="fact_sales")
        params_base.update(sales_shop_params)
        
        # Build base WHERE conditions for sales (filtered by periodRange and shop)
        sales_where = ["user_id = CAST(:user_id AS uuid)"]
        if sales_shop_filter:
            sales_where.append(sales_shop_filter)
        if date_from:
            sales_where.append("date_created >= CAST(:date_from AS date)")
        sales_where.append("date_created < CAST(:date_to AS date) + INTERVAL '1 day'")
        
        sales_where_clause = " AND ".join(sales_where)
        
        # Prepare params for sales query
        sales_params = {**params_base}
        if date_from:
            sales_params["date_from"] = date_from.isoformat()
        
        # A) SALES aggregation
        # Use shared status conditions from utils.metrics to ensure consistency with Charts
        status_conditions = get_status_conditions()
        processing_status_condition = status_conditions['processing']
        completed_status_condition = status_conditions['completed']
        cancelled_status_condition = status_conditions['cancelled']
        
        # Define conditions for use in other queries
        completed_condition = completed_status_condition
        # Orders condition: all orders except cancelled
        orders_condition = "lower(trim(status)) NOT IN ('отменен', 'отменено', 'cancelled', 'canceled')"
        
        # Control SQL for verification (not executed, for reference):
        # Заказы: SELECT SUM(qty), SUM(revenue_sum) FROM fact_sales WHERE ...
        # В обработке: SELECT SUM(qty), SUM(revenue_sum) FROM fact_sales WHERE ... AND lower(trim(status))='в обработке'
        # Выкупы: SELECT SUM(qty), SUM(revenue_sum) FROM fact_sales WHERE ... AND lower(trim(status))='завершен'
        # Возвраты сумма: SELECT SUM(returns_qty * price_sum) FROM fact_sales WHERE ... AND lower(trim(status)) IN ('завершен', 'отменен/отменён')
        # Return rate: SELECT (SUM(returns_qty)/NULLIF(SUM(qty),0))*100 FROM fact_sales WHERE ...
        # Avg check: SELECT SUM(revenue_sum)/NULLIF(SUM(qty),0) FROM fact_sales WHERE ... AND lower(trim(status))='завершен'
        
        sales_query = text(f"""
            SELECT 
                -- ordersCount: SUM(qty) WITHOUT status filter
                COALESCE(SUM(qty), 0) as orders_count,
                -- ordersValue: ТЗ: SUM(Количество * Цена (сумы)) БЕЗ фильтра по статусу (как orders_count)
                COALESCE(SUM(COALESCE(qty, 0) * COALESCE(price_sum, 0)), 0) as orders_value,
                -- processingCount/processingValue: SUM(qty) and SUM(revenue_sum) WHERE status='в обработке'
                COALESCE(SUM(CASE WHEN {processing_status_condition} THEN qty ELSE 0 END), 0) as processing_count,
                COALESCE(SUM(CASE WHEN {processing_status_condition} THEN revenue_sum ELSE 0 END), 0) as processing_value,
                -- completedCount/completedValue: SUM(qty) and SUM(revenue_sum) WHERE status='завершен'
                COALESCE(SUM(CASE WHEN {completed_status_condition} THEN qty ELSE 0 END), 0) as completed_count,
                COALESCE(SUM(CASE WHEN {completed_status_condition} THEN revenue_sum ELSE 0 END), 0) as completed_value,
                -- returnsCount: SUM(returns_qty) from all rows (same filters period/shop)
                COALESCE(SUM(returns_qty), 0) as returns_count,
                -- returnsValue: SUM(returns_qty * price_sum) WHERE status IN ('завершен', 'отменен/отменён')
                COALESCE(SUM(
                    CASE 
                        WHEN ({completed_status_condition} OR {cancelled_status_condition})
                        THEN COALESCE(returns_qty, 0) * COALESCE(price_sum, 0)
                        ELSE 0
                    END
                ), 0) as returns_value,
                -- returnsValueCompleted: SUM(returns_qty * price_sum) WHERE status='завершен' (только для завершенных заказов)
                COALESCE(SUM(
                    CASE 
                        WHEN {completed_status_condition}
                        THEN COALESCE(returns_qty, 0) * COALESCE(price_sum, 0)
                        ELSE 0
                    END
                ), 0) as returns_value_completed,
                -- uzumCommission/uzumLogistics: только completed
                COALESCE(SUM(CASE WHEN {completed_status_condition} THEN commission_sum ELSE 0 END), 0) as uzum_commission,
                COALESCE(SUM(CASE WHEN {completed_status_condition} THEN logistics_sum ELSE 0 END), 0) as uzum_logistics,
                -- productCost: completed OR processing (для productCost в ответе)
                COALESCE(SUM(
                    CASE 
                        WHEN {completed_status_condition} OR {processing_status_condition}
                        THEN cogs_sum 
                        ELSE 0 
                    END
                ), 0) as product_cost_total,
                -- productCost: completed (для salesProfitability и ROI)
                COALESCE(SUM(CASE WHEN {completed_status_condition} THEN cogs_sum ELSE 0 END), 0) as product_cost_completed
            FROM {qname("fact_sales")}
            WHERE {sales_where_clause}
        """)
        
        sales_result = db.execute(sales_query, sales_params)
        sales_row = sales_result.fetchone()
        
        orders_count = float(sales_row[0] or 0)
        orders_value = float(sales_row[1] or 0)  # ТЗ: SUM(qty * price_sum) БЕЗ фильтра по статусу
        processing_count = float(sales_row[2] or 0)
        processing_value = float(sales_row[3] or 0)
        completed_count = float(sales_row[4] or 0)
        completed_value = float(sales_row[5] or 0)
        returns_count = float(sales_row[6] or 0)
        returns_value = float(sales_row[7] or 0)
        returns_value_completed = float(sales_row[8] or 0)
        uzum_commission = float(sales_row[9] or 0)
        uzum_logistics = float(sales_row[10] or 0)
        product_cost_total = float(sales_row[11] or 0)
        product_cost_completed = float(sales_row[12] or 0)
        
        # Лог для проверки формулы orders_value (dev only)
        logger.info(
            f"orders_revenue calculation: orders_value={orders_value} (SUM(qty * price_sum) без фильтра по статусу), "
            f"orders_count={orders_count}, "
            f"period={period_code}, shop_id={shop_id}"
        )
        
        # Derived metrics from sales
        # Return rate: (SUM(returns_qty) / SUM(qty)) * 100 (from all rows, same filters)
        return_rate = (returns_count / orders_count * 100) if orders_count > 0 else 0.0
        # Average check: SUM(revenue_sum)/SUM(qty) WHERE status='завершен'
        average_check = (completed_value / completed_count) if completed_count > 0 else 0.0
        # Round average_check to integer (no kopecks) - as per TZ
        average_check = round(average_check) if average_check > 0 else 0.0
        revenue = completed_value
        
        # Debug log for returns metrics
        logger.info(
            f"returns metrics: returns_count={returns_count}, returns_value={returns_value}, "
            f"period={period_code}, shop_id={shop_id}"
        )
        
        # B) EXPENSES aggregation (filtered by periodRange)
        expenses_where = ["user_id = CAST(:user_id AS uuid)"]
        if date_from:
            expenses_where.append("date_written_off >= CAST(:date_from AS date)")
        expenses_where.append("date_written_off < CAST(:date_to AS date) + INTERVAL '1 day'")
        
        expenses_where_clause = " AND ".join(expenses_where)
        
        # Prepare params for expenses query
        expenses_params = {**params_base}
        if date_from:
            expenses_params["date_from"] = date_from.isoformat()
        
        expenses_query = text(f"""
            SELECT 
                -- uzumAds: Источник="Маркетинг" AND Тип операции="Оплата"
                -- ТЗ: expenses-report: sum(Стоимость (сумы)) where Источник="Маркетинг" AND Тип операции="Оплата"
                COALESCE(SUM(
                    CASE 
                        WHEN (COALESCE(source, '') ILIKE '%маркетинг%' OR COALESCE(source, '') ILIKE '%marketing%')
                             AND (COALESCE(operation_type, '') ILIKE '%оплат%' OR COALESCE(operation_type, '') ILIKE '%payment%')
                        THEN COALESCE(cost_sum, 0)
                        ELSE 0
                    END
                ), 0) as uzum_ads,
                -- uzumStorage: определяется только по Тип операции
                -- ТЗ: sum(Стоимость) где Тип операции='Оплата' → прибавляется, 'Возврат' → вычитается
                -- Фильтр по Услуга убран согласно обновлённому ТЗ
                COALESCE(SUM(
                    CASE 
                        WHEN lower(trim(COALESCE(operation_type, ''))) = 'оплата' 
                        THEN COALESCE(cost_sum, 0)
                        WHEN lower(trim(COALESCE(operation_type, ''))) = 'возврат' 
                        THEN -COALESCE(cost_sum, 0)
                        ELSE 0
                    END
                ), 0) as uzum_storage,
                -- uzumFines: Услуга ILIKE '%Штраф%'
                -- ТЗ: expenses-report: sum(Сумма (сумы)) where Услуга ILIKE '%Штраф%'
                COALESCE(SUM(
                    CASE 
                        WHEN COALESCE(service, '') ILIKE '%штраф%'
                        THEN COALESCE(amount_sum, 0)
                        ELSE 0
                    END
                ), 0) as uzum_fines
            FROM {qname("fact_expenses")}
            WHERE {expenses_where_clause}
        """)
        
        expenses_result = db.execute(expenses_query, expenses_params)
        expenses_row = expenses_result.fetchone()
        
        uzum_ads = float(expenses_row[0] or 0)
        uzum_storage = float(expenses_row[1] or 0)
        uzum_fines = float(expenses_row[2] or 0)
        
        # Налоги 1% от выручки (завершённые заказы)
        # ТЗ: Налоги 1% = Выручка * 0.01, где Выручка = SUM(Выручка (сумы)) со статусом "Завершен"
        taxes_1pct = revenue * 0.01 if revenue else 0.0
        
        # Доп. расходы = COALESCE(SUM(amount_sum), 0) из manual_expenses (тот же источник, что и таблица "Доп. расходы")
        # Фильтры: период (expense_date), магазин по названию (shop_norm) или shop_id (UUID), user_id, is_deleted = false
        # Магазин: как в GET /api/extra-expenses — по колонке "Магазин" (dim_shop.shop_name), нормализованно (trim, пробелы, upper)
        manual_expenses_params = {**params_base}
        date_from_filter = ""
        if date_from:
            manual_expenses_params["date_from"] = date_from.isoformat()
            date_from_filter = "AND e.expense_date >= CAST(:date_from AS date)"
        manual_shop_filter = ""
        if shop_norm:
            manual_shop_filter = "AND upper(regexp_replace(trim(COALESCE(ds.shop_name, '')), '\\s+', ' ', 'g')) = :shop_norm"
        elif shop_id:
            manual_shop_filter = "AND e.shop_id = CAST(:shop_id AS uuid)"
        manual_expenses_query = text(f"""
            SELECT COALESCE(SUM(e.amount_sum), 0) AS extra_sum
            FROM {qname("manual_expenses")} e
            LEFT JOIN {qname("dim_shop")} ds ON ds.shop_id = e.shop_id AND ds.user_id = e.user_id
            WHERE e.user_id = CAST(:user_id AS uuid)
              AND e.is_deleted = false
              {date_from_filter}
              AND e.expense_date <= CAST(:date_to AS date)
              {manual_shop_filter}
        """)
        manual_expenses_result = db.execute(manual_expenses_query, manual_expenses_params)
        manual_expenses_row = manual_expenses_result.fetchone()
        extra_expenses = float(manual_expenses_row[0] or 0) if manual_expenses_row else 0.0
        logger.info(f"extra_expenses: period={period_code}, date_to={date_to_iso}, shop_norm={shop_norm}, shop_id={shop_id}, value={extra_expenses}")
        
        # C) Total expenses, profit, ratios
        # ТЗ: Расходы в блоке Финансы = сумма выбранных строк из блока Расходы:
        # Комиссия UZUM + Логистика UZUM + Себест. прод. тов. + Налоги 1% + Доп. расходы
        # Формула применяется одинаково для всех магазинов и для выбранного магазина
        # (компоненты уже отфильтрованы по shop_id, если он задан)
        total_expenses = (
            (uzum_commission or 0.0) +
            (uzum_logistics or 0.0) +
            (product_cost_total or 0.0) +
            (taxes_1pct or 0.0) +
            (extra_expenses or 0.0)
        )
        
        # DEBUG: Логируем состав total_expenses для проверки
        logger.info(f"[DEBUG] total_expenses breakdown: commission={uzum_commission}, logistics={uzum_logistics}, product_cost={product_cost_total}, taxes={taxes_1pct}, extra_expenses={extra_expenses}, total={total_expenses}")
        
        profit = revenue - total_expenses
        
        # ТЗ: Рентабельность продаж = (Прибыль / Выручка) * 100%
        # Формула: profitability_pct = COALESCE((profit / NULLIF(revenue, 0)) * 100, 0)
        # Защита: если revenue = 0 -> 0
        sales_profitability = (profit / revenue * 100) if revenue > 0 else 0.0
        
        # ТЗ: Окупаемость инвестиций = (Прибыль / Расходы) * 100%
        # Защита: если Расходы = 0 -> 0
        # Формула: roi = (profit / expenses) * 100, если expenses > 0, иначе 0
        roi = (profit / total_expenses * 100) if total_expenses > 0 else 0.0
        
        logger.info(f"expenses: shop_id={shop_id}, total_expenses={total_expenses}, commission={uzum_commission}, logistics={uzum_logistics}, product_cost_total={product_cost_total}, taxes_1pct={taxes_1pct}, extra_expenses={extra_expenses}, ads={uzum_ads}, storage={uzum_storage}, fines={uzum_fines}, product_cost_completed={product_cost_completed}, salesProfitability={sales_profitability}, roi={roi}")
        
        # D) Revenue trend (compare with previous period)
        # ТЗ: Тренд выручки = сравнение выручки выбранного периода с выручкой аналогичного периода ранее
        # Реализовать: current_revenue, previous_revenue, delta_abs, delta_pct
        # "Аналогичный период ранее" = такой же по длине интервал непосредственно перед текущим
        revenue_trend = 0.0
        revenue_trend_detail = {
            "current_revenue": revenue,
            "previous_revenue": 0.0,
            "delta_abs": 0.0,
            "delta_pct": 0.0
        }
        
        if period_code != "all" and date_from:
            # Calculate previous period range (same length as current period)
            # ТЗ: Если текущий период [from, to], длина L = (to - from + 1 день)
            # Previous период = [from - L, to - L]
            period_length_days = (date_to_date - date_from).days + 1  # L = (to - from + 1)
            prev_date_from = date_from - timedelta(days=period_length_days)  # from - L
            prev_date_to = date_to_date - timedelta(days=period_length_days)  # to - L
            
            prev_params = {**params_base, "prev_date_from": prev_date_from.isoformat(), "prev_date_to": prev_date_to.isoformat()}
            
            prev_where = ["user_id = CAST(:user_id AS uuid)"]
            prev_where.append("date_created >= CAST(:prev_date_from AS date)")
            prev_where.append("date_created < CAST(:prev_date_to AS date) + INTERVAL '1 day'")
            if sales_shop_filter:
                prev_where.append(sales_shop_filter)
            
            prev_where_clause = " AND ".join(prev_where)
            
            prev_revenue_query = text(f"""
                SELECT COALESCE(SUM(CASE WHEN ({completed_condition}) THEN revenue_sum ELSE 0 END), 0)
                FROM {qname("fact_sales")}
                WHERE {prev_where_clause}
            """)
            
            prev_revenue_result = db.execute(prev_revenue_query, prev_params)
            prev_revenue = float(prev_revenue_result.scalar() or 0)
            
            # Calculate trend metrics
            revenue_trend_detail["previous_revenue"] = prev_revenue
            revenue_trend_detail["delta_abs"] = revenue - prev_revenue
            
            # ТЗ: Тренд выручки = ((current_revenue - previous_revenue) / previous_revenue) * 100%
            # Защита: если previous_revenue = 0 -> 0 (не показывать рост как 100%)
            if prev_revenue > 0:
                revenue_trend = ((revenue - prev_revenue) / prev_revenue * 100)
                revenue_trend_detail["delta_pct"] = revenue_trend
            else:
                # Если previous_revenue = 0, возвращаем 0 (не показываем рост)
                revenue_trend = 0.0
                revenue_trend_detail["delta_pct"] = 0.0
        
        # E) Cumulative revenue — ИСКЛЮЧЕНИЕ: всегда вся выручка пользователя (без дат и без магазина)
        # То же, что GET /api/kpi/cumulative-revenue: SUM(revenue_sum) WHERE user_id AND completed
        cumulative_query = text(f"""
            SELECT COALESCE(SUM(revenue_sum), 0)
            FROM {qname("fact_sales")}
            WHERE user_id = CAST(:user_id AS uuid)
              AND ({completed_condition})
        """)
        cumulative_result = db.execute(cumulative_query, {"user_id": str(user_id)})
        cumulative_revenue = float(cumulative_result.scalar() or 0)
        logger.info(f"cumulativeRevenue (global, unfiltered): user_id={user_id}, value={cumulative_revenue}")
        
        # F) STOCK aggregation — источник: left-out-report_old (fact_leftout_old_snapshot или stg_leftout_old fallback)
        # Товаров на складе = SUM(in_sale_qty), Себест. тов. = SUM(in_sale_qty * cost_sum), Рознич. цена = SUM(in_sale_qty * price_sum)
        # Последний батч: строго upload_batch_id для leftout_old (MAX(loaded_at) по fact → один batch_id).
        # Фильтр магазина: баркоды выбранного магазина из fact_storage_snapshot (последний снапшот storage); по shop_norm (shop_raw) или по shop_id (dim_shop).
        stock_quantity = 0.0
        stock_cost = 0.0
        stock_retail_price = 0.0
        stock_sku_total = 0
        stock_sku_with_stock = 0
        stock_snapshot_at = None
        stock_is_zero = False
        stock_zero_reason = None
        stock_source = None  # "fact" when data from fact_leftout_old_snapshot
        stock_batch_id = None
        stock_loaded_at = None

        stock_old_table = qname("fact_leftout_old_snapshot")
        has_stock_old_table = db.execute(
            text("SELECT to_regclass(:t) IS NOT NULL"), {"t": stock_old_table}
        ).scalar()

        stock_params_base = {"user_id": str(user_id)}
        leftout_old_filter = ""
        if shop_norm:
            stock_params_base["shop_norm"] = shop_norm
            leftout_old_filter = "\n                " + storage_barcode_filter_sql("lo", prefix_and=True, outer_barcode_norm_expr=barcode_norm_sql("lo.barcode"))
        elif shop_id:
            stock_params_base["shop_id"] = shop_id
            leftout_old_filter = "\n                " + storage_barcode_filter_by_shop_id_sql("lo", prefix_and=True, outer_barcode_norm_expr=barcode_norm_sql("lo.barcode"))

        if has_stock_old_table:
            # 1) Последний батч строго для leftout_old: batch с MAX(loaded_at)
            batch_select = text(f"""
                SELECT upload_batch_id, loaded_at
                FROM (
                    SELECT upload_batch_id, MAX(loaded_at) AS loaded_at
                    FROM {stock_old_table} lo
                    WHERE lo.user_id = CAST(:user_id AS uuid)
                    {leftout_old_filter}
                    GROUP BY upload_batch_id
                ) sub
                ORDER BY loaded_at DESC
                LIMIT 1
            """)
            try:
                batch_row = db.execute(batch_select, stock_params_base).fetchone()
            except Exception as e:
                logger.warning(f"stock (leftout_old): batch select failed: {e}")
                batch_row = None
            if batch_row:
                stock_batch_id, stock_loaded_at = batch_row[0], batch_row[1]
                stock_params = {**stock_params_base, "stock_batch_id": str(stock_batch_id)}
                stock_query = text(f"""
                    SELECT
                        COUNT(*) AS stock_sku_total,
                        COALESCE(SUM(COALESCE(lo.in_sale_qty, 0)), 0) AS stock_quantity,
                        SUM(CASE WHEN COALESCE(lo.in_sale_qty, 0) > 0 THEN 1 ELSE 0 END) AS stock_sku_with_stock,
                        MAX(lo.loaded_at) AS stock_snapshot_at,
                        COALESCE(SUM(COALESCE(lo.in_sale_qty, 0) * COALESCE(lo.price_sum, 0)), 0) AS stock_retail_price,
                        COALESCE(SUM(COALESCE(lo.in_sale_qty, 0) * COALESCE(lo.cost_sum, 0)), 0) AS stock_cost
                    FROM {stock_old_table} lo
                    WHERE lo.user_id = CAST(:user_id AS uuid)
                        AND lo.upload_batch_id = CAST(:stock_batch_id AS uuid)
                        {leftout_old_filter}
                """)
                try:
                    stock_result = db.execute(stock_query, stock_params)
                    stock_row = stock_result.fetchone()
                    if stock_row:
                        stock_sku_total = int(stock_row[0] or 0)
                        stock_quantity = float(stock_row[1] or 0)
                        stock_sku_with_stock = int(stock_row[2] or 0)
                        stock_snapshot_at = stock_row[3]
                        stock_retail_price = float(stock_row[4] or 0)
                        stock_cost = float(stock_row[5] or 0)
                        stock_source = "fact"
                        logger.info(
                            f"stock (leftout_old): source=fact, batch_id={stock_batch_id}, loaded_at={stock_loaded_at}, "
                            f"row_count={stock_sku_total}, sum_in_sale={stock_quantity}, shop_norm={shop_norm}, shop_id={shop_id}"
                        )
                        # stock_is_zero / stock_has_data финально выставляются ниже
                except Exception as e:
                    logger.warning(f"stock (leftout_old): fact aggregation query failed: {e}")

        # Явные флаги: не путать "нет данных" и "0"
        # stock_has_data = есть строки в последнем batch leftout_old (после фильтра магазина)
        # stock_is_zero = только когда есть данные и SUM(В продаже)=0
        stock_has_data = (stock_source is not None and stock_sku_total > 0)
        stock_is_zero = (stock_has_data and stock_quantity == 0)
        if stock_source is None:
            stock_zero_reason = "no_snapshot_data"
        elif stock_has_data and stock_quantity == 0:
            stock_zero_reason = "all_zero_in_snapshot"
        elif not stock_has_data:
            stock_zero_reason = "no_snapshot_data"
        else:
            stock_zero_reason = None
        # Для API: единый идентификатор источника
        stock_source_api = "leftout_old" if stock_source == "fact" else None

        if stock_retail_price is None:
            stock_retail_price = 0.0
        if stock_cost is None:
            stock_cost = 0.0
        # Склад: если данных нет — возвращать "нет данных", а не 0
        if not stock_has_data:
            stock_quantity_out = "нет данных"
            stock_cost_out = "нет данных"
            stock_retail_price_out = "нет данных"
        else:
            stock_quantity_out = stock_quantity
            stock_cost_out = stock_cost
            stock_retail_price_out = stock_retail_price
        logger.info(
            f"stock (leftout_old): source={stock_source}, source_api={stock_source_api}, batch_id={stock_batch_id}, loaded_at={stock_loaded_at}, "
            f"quantity={stock_quantity}, cost={stock_cost}, retail_price={stock_retail_price}, "
            f"sku_total={stock_sku_total}, sku_with_stock={stock_sku_with_stock}, has_data={stock_has_data}, is_zero={stock_is_zero}, reason={stock_zero_reason}, shop_norm={shop_norm}"
        )

        # Для lost_revenue оставляем источник fact_leftout_snapshot (новый формат); фильтр по магазину тот же
        leftout_max_filter = ""
        if shop_norm:
            leftout_max_filter = "\n                " + storage_barcode_filter_sql("fact_leftout_snapshot", prefix_and=True)
        elif shop_id:
            leftout_max_filter = "AND (:shop_id IS NULL OR shop_id = CAST(:shop_id AS uuid))"

        # B) Lost revenue: потенциальная выручка от товаров без остатков
        # Формула: (avg_daily_sales * 15) * price (для товаров где stock=0 и avg_daily_sales>0)
        # Prepare params for lost revenue query
        lost_revenue_params = {**params_base}
        
        # Calculate days_in_period: для all использовать 90 дней, иначе (date_to - date_from + 1)
        if date_from is None:
            # period=all: для расчета avg использовать date_from = date_to - 89 days
            date_from_for_avg = date_to_date - timedelta(days=89)
            days_in_period = 90
        else:
            date_from_for_avg = date_from
            days_in_period = (date_to_date - date_from).days + 1
        
        lost_revenue_params["date_from_for_avg"] = date_from_for_avg.isoformat()
        lost_revenue_params["days_in_period"] = days_in_period
        
        # Price window fallback: последние 90 дней до date_to
        price_window_from_date = date_to_date - timedelta(days=89)
        price_window_from = price_window_from_date.isoformat()
        price_window_to = date_to_iso
        lost_revenue_params["price_window_from"] = price_window_from
        
        # A) Определить snap_loaded_at (самый свежий snapshot до date_to; фильтр shop = leftout_max_filter)
        # Используем fact_leftout_snapshot как единый источник склада
        snap_loaded_at_query = text(f"""
            SELECT MAX(loaded_at) AS snap_loaded_at
            FROM {qname("fact_leftout_snapshot")}
            WHERE user_id = CAST(:user_id AS uuid)
                {leftout_max_filter}
                AND loaded_at < CAST(:date_to AS date) + INTERVAL '1 day'
        """)
        
        snap_loaded_at_result = db.execute(snap_loaded_at_query, lost_revenue_params)
        snap_loaded_at = snap_loaded_at_result.scalar()
        
        # Если нет снапшота => lostRevenue = 0
        if snap_loaded_at is None:
            lost_revenue = 0.0
            rows_snapshot = 0
            rows_zero_stock = 0
            rows_with_sales = 0
            rows_with_price = 0
            rows_no_price = 0
            logger.info(f"lostRevenue: no snapshot, period={period_code}, date_from={date_from_iso or 'NULL'}, date_to={date_to_iso}, shop_id={shop_id}")
        else:
            lost_revenue_params["snap_loaded_at"] = snap_loaded_at
            
            # B) Расчет lostRevenue с avg_daily_sales из периода и ценами
            # ТЗ: Упущенная выручка = (Среднесуточные продажи FBO за 15 дней, шт) * Цена (сумы) * 15
            # Условие: Остатки FBO (всего в продаже и на СДХ), шт = 0
            # Цена: weighted_avg_price = SUM(revenue_sum)/NULLIF(SUM(qty),0) по завершенным заказам
            # Для avg_daily_sales используем завершенные заказы за период
            # Если period=all, используем последние 90 дней для расчета цены (зафиксировано в комментарии)
            lost_revenue_query = text(f"""
                WITH period_sales AS (
                    -- Среднесуточные продажи FBO за период (только завершенные заказы)
                    -- Приоритет сопоставления: barcode_norm (если не NULL), затем sku
                    -- barcode_norm вычисляется на лету: нормализация barcode (удаление пробелов)
                    SELECT
                        NULLIF(TRIM(sku), '') AS sku,
                        {barcode_norm_sql('barcode')} AS barcode_norm,
                        SUM(qty) AS qty_period,
                        SUM(revenue_sum) AS rev_period
                    FROM {qname("fact_sales")}
                    WHERE user_id = CAST(:user_id AS uuid)
                        AND ({completed_condition})
                        {f'AND {sales_shop_filter}' if sales_shop_filter else ''}
                        AND date_created >= CAST(:date_from_for_avg AS date)
                        AND date_created < CAST(:date_to AS date) + INTERVAL '1 day'
                    GROUP BY NULLIF(TRIM(sku), ''), {barcode_norm_sql('barcode')}
                ),
                price_window AS (
                    -- Weighted average price из окна для расчета цены (только завершенные заказы)
                    SELECT
                        NULLIF(TRIM(sku), '') AS sku,
                        {barcode_norm_sql('barcode')} AS barcode_norm,
                        SUM(revenue_sum) AS rev_window,
                        SUM(qty) AS qty_window
                    FROM {qname("fact_sales")}
                    WHERE user_id = CAST(:user_id AS uuid)
                        AND ({completed_condition})
                        {f'AND {sales_shop_filter}' if sales_shop_filter else ''}
                        AND date_created >= CAST(:price_window_from AS date)
                        AND date_created < CAST(:date_to AS date) + INTERVAL '1 day'
                    GROUP BY NULLIF(TRIM(sku), ''), {barcode_norm_sql('barcode')}
                ),
                snap AS (
                    -- Текущий snapshot склада из fact_leftout_snapshot; фильтр shop = leftout_max_filter
                    SELECT
                        NULLIF(TRIM(sku), '') AS sku,
                        {barcode_norm_sql('barcode')} AS barcode_norm,
                        COALESCE(in_sale, 0) + COALESCE(sdh_stock, 0) AS stock_fbo
                    FROM {qname("fact_leftout_snapshot")}
                    WHERE user_id = CAST(:user_id AS uuid)
                        {leftout_max_filter}
                        AND loaded_at = CAST(:snap_loaded_at AS timestamp)
                )
                SELECT
                    COUNT(*) AS rows_snapshot,
                    SUM(CASE WHEN p.stock_fbo = 0 THEN 1 ELSE 0 END) AS rows_zero_stock,
                    SUM(CASE WHEN p.stock_fbo = 0 AND COALESCE(p.qty_period, 0) > 0 THEN 1 ELSE 0 END) AS rows_with_sales,
                    SUM(CASE WHEN p.stock_fbo = 0 AND COALESCE(p.qty_period, 0) > 0 AND p.weighted_price IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_price,
                    SUM(CASE WHEN p.stock_fbo = 0 AND COALESCE(p.qty_period, 0) > 0 AND p.weighted_price IS NULL THEN 1 ELSE 0 END) AS rows_no_price,
                    COALESCE(SUM(
                        CASE
                            WHEN p.stock_fbo = 0 
                                AND COALESCE(p.qty_period, 0) > 0 
                                AND p.weighted_price IS NOT NULL
                            THEN ((p.qty_period::numeric / CAST(:days_in_period AS numeric)) * 15 * p.weighted_price)
                            ELSE 0
                        END
                    ), 0) AS lost_revenue
                FROM (
                    SELECT 
                        s.sku,
                        s.barcode_norm,
                        s.stock_fbo,
                        ps.qty_period,
                        -- Weighted average price: SUM(revenue_sum)/NULLIF(SUM(qty),0) по завершенным
                        COALESCE(
                            -- Цена из периода (weighted avg)
                            CASE WHEN ps.qty_period > 0 THEN ps.rev_period / NULLIF(ps.qty_period, 0) END,
                            -- Fallback цена из окна (weighted avg)
                            CASE WHEN pw.qty_window > 0 THEN pw.rev_window / NULLIF(pw.qty_window, 0) END
                        ) AS weighted_price
                    FROM snap s
                    LEFT JOIN period_sales ps ON (
                        -- Приоритет 1: сопоставление по barcode_norm
                        (ps.barcode_norm = s.barcode_norm AND s.barcode_norm IS NOT NULL AND ps.barcode_norm IS NOT NULL)
                        OR
                        -- Приоритет 2: сопоставление по sku (fallback)
                        (ps.barcode_norm IS NULL AND s.barcode_norm IS NULL AND ps.sku = s.sku AND s.sku IS NOT NULL AND ps.sku IS NOT NULL)
                    )
                    LEFT JOIN price_window pw ON (
                        -- Приоритет 1: сопоставление по barcode_norm
                        (pw.barcode_norm = s.barcode_norm AND s.barcode_norm IS NOT NULL AND pw.barcode_norm IS NOT NULL)
                        OR
                        -- Приоритет 2: сопоставление по sku (fallback)
                        (pw.barcode_norm IS NULL AND s.barcode_norm IS NULL AND pw.sku = s.sku AND s.sku IS NOT NULL AND pw.sku IS NOT NULL)
                    )
                ) p
            """)
            
            lost_revenue_result = db.execute(lost_revenue_query, lost_revenue_params)
            lost_revenue_row = lost_revenue_result.fetchone()
            
            if lost_revenue_row:
                rows_snapshot = int(lost_revenue_row[0] or 0)
                rows_zero_stock = int(lost_revenue_row[1] or 0)
                rows_with_sales = int(lost_revenue_row[2] or 0)
                rows_with_price = int(lost_revenue_row[3] or 0)
                rows_no_price = int(lost_revenue_row[4] or 0)
                lost_revenue = float(lost_revenue_row[5] or 0)
            else:
                rows_snapshot = 0
                rows_zero_stock = 0
                rows_with_sales = 0
                rows_with_price = 0
                rows_no_price = 0
                lost_revenue = 0.0
            
            logger.info(f"lostRevenue: value={lost_revenue}, days_in_period={days_in_period}, rows_snapshot={rows_snapshot}, rows_zero_stock={rows_zero_stock}, rows_with_sales={rows_with_sales}, rows_with_price={rows_with_price}, rows_no_price={rows_no_price}, snap_loaded_at={snap_loaded_at}, period={period_code}, date_from={date_from_iso or 'NULL'}, date_to={date_to_iso}, shop_id={shop_id}")
        
        # Для совместимости оставляем старые поля (можно удалить позже)
        lost_revenue_end = lost_revenue
        lost_revenue_peak = lost_revenue
        lost_revenue_delta = lost_revenue
        
        return {
            "cumulativeRevenue": cumulative_revenue,
            "ordersCount": orders_count,
            "ordersValue": orders_value,
            "processingCount": processing_count,
            "processingValue": processing_value,
            "completedCount": completed_count,
            "completedValue": completed_value,
            "returnsCount": returns_count,
            "returnsValue": returns_value,
            "returnRate": return_rate,
            "averageCheck": average_check,
            "revenue": revenue,
            "totalExpenses": total_expenses,
            "profit": profit,
            "salesProfitability": sales_profitability,
            "roi": roi,
            "revenueTrend": revenue_trend,  # Legacy: percentage change (for backward compatibility)
            "revenueTrendDetail": revenue_trend_detail,  # New: detailed trend object with current, previous, delta_abs, delta_pct
            "lostRevenue": lost_revenue,
            "lostRevenueEnd": lost_revenue_end,
            "lostRevenuePeak": lost_revenue_peak,
            "lostRevenueDelta": lost_revenue_delta,
            "lostRevenueDebug": {
                "snap_loaded_at": snap_loaded_at.isoformat() if snap_loaded_at and hasattr(snap_loaded_at, 'isoformat') else (str(snap_loaded_at) if snap_loaded_at else None),
                "days_in_period": days_in_period,
                "rows_snapshot": rows_snapshot,
                "rows_zero_stock": rows_zero_stock,
                "rows_with_sales": rows_with_sales,
                "rows_with_price": rows_with_price,
                "rows_no_price": rows_no_price
            },
            "uzumCommission": uzum_commission,
            "uzumLogistics": uzum_logistics,
            "uzumAds": uzum_ads,
            "uzumStorage": uzum_storage,
            "uzumFines": uzum_fines,
            "taxes1pct": taxes_1pct,
            "productCost": product_cost_total,
            "productCostCompleted": product_cost_completed,
            "extraExpenses": extra_expenses,
            "stockQuantity": stock_quantity_out,
            "stockCost": stock_cost_out,
            "stockRetailPrice": stock_retail_price_out,
            "stockSkuTotal": stock_sku_total,
            "stockSkuWithStock": stock_sku_with_stock,
            "stockSnapshotAt": stock_snapshot_at.isoformat() if stock_snapshot_at and hasattr(stock_snapshot_at, 'isoformat') else (str(stock_snapshot_at) if stock_snapshot_at else None),
            "stockHasData": stock_has_data,
            "stockIsZero": stock_is_zero,
            "stockZeroReason": stock_zero_reason,
            "stockSource": stock_source_api,
            "stockBatchId": str(stock_batch_id) if stock_batch_id else None,
            "period_range": period_range_dict
        }
        
    except HTTPException:
        raise
    except Exception as e:
        err_msg = str(e).lower()
        if "barcode_norm" in err_msg or "does not exist" in err_msg:
            logger.warning(f"kpi_summary: missing column barcode_norm (migration not applied): {e}")
            raise HTTPException(
                status_code=500,
                detail="Run alembic upgrade head. Column app.fact_storage_snapshot.barcode_norm or app.fact_leftout_snapshot.barcode_norm may be missing."
            )
        logger.error(f"Error in kpi_summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/kpi/cumulative-revenue", response_model=CumulativeRevenueResponse)
def get_cumulative_revenue_global(
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Общая накопительная выручка пользователя за всё время.
    Не зависит от фильтров магазина и периода: SUM(revenue_sum) по всем данным пользователя (status завершен).
    """
    completed_condition = get_status_sql_condition("completed")
    query = text(f"""
        SELECT COALESCE(SUM(revenue_sum), 0)
        FROM {qname("fact_sales")}
        WHERE user_id = CAST(:user_id AS uuid)
          AND ({completed_condition})
    """)
    result = db.execute(query, {"user_id": str(user_id)})
    cumulative_revenue = float(result.scalar() or 0)
    logger.info(f"cumulative-revenue (global): user_id={user_id}, value={cumulative_revenue}")
    return CumulativeRevenueResponse(cumulativeRevenue=cumulative_revenue)
