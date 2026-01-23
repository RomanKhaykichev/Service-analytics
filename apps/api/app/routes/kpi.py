from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta
import logging
from app.db import get_db, qname
from app.deps import require_user
from app.utils.statuses import get_status_sql_condition
from fastapi import Depends

logger = logging.getLogger(__name__)
router = APIRouter()


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


@router.get("/kpi/summary")
def kpi_summary(
    request: Request,
    period: str = "30d",
    shop_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    user_id = require_user(request)
    
    # Normalize period
    period_code = normalize_period(period)
    
    # Get data_end_date (maximum date from all data tables)
    data_end_date = get_data_end_date(db, user_id)
    
    # Calculate period range based on data_end_date
    period_range_dict = period_range(period_code, data_end_date)
    date_to_iso = period_range_dict["date_to"]
    
    # Protection: if date_to is None, use today
    if date_to_iso is None:
        date_to_date = datetime.now().date()
        date_to_iso = date_to_date.isoformat()
    else:
        date_to_date = datetime.fromisoformat(date_to_iso).date()
    
    date_from_iso = period_range_dict["date_from"]
    date_from = datetime.fromisoformat(date_from_iso).date() if date_from_iso else None
    
    # Validate shop_id if provided
    if shop_id:
        try:
            UUID(shop_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid shop_id format (must be UUID)"
            )
    
    logger.info(f"kpi_summary: user_id={user_id}, shop_id={shop_id}, period={period_code}, period_range={period_range_dict}")
    
    try:
        # Base parameters - ALWAYS includes user_id and date_to
        params_base = {
            "user_id": str(user_id),
            "date_to": date_to_iso,
            "shop_id": shop_id,  # Can be None
        }
        
        # Build base WHERE conditions for sales (filtered by periodRange)
        sales_where = [
            "user_id = CAST(:user_id AS uuid)",
            "(:shop_id IS NULL OR shop_id = CAST(:shop_id AS uuid))"
        ]
        if date_from:
            sales_where.append("date_created >= CAST(:date_from AS date)")
        sales_where.append("date_created < CAST(:date_to AS date) + INTERVAL '1 day'")
        
        sales_where_clause = " AND ".join(sales_where)
        
        # Prepare params for sales query
        sales_params = {**params_base}
        if date_from:
            sales_params["date_from"] = date_from.isoformat()
        
        # A) SALES aggregation
        # Status normalization: lower(trim(status))
        # According to TZ: exact match with normalized status
        processing_status_condition = "lower(trim(status)) = 'в обработке'"
        # Completed: support both 'завершен' and 'завершён' (with ё)
        completed_status_condition = "lower(trim(status)) IN ('завершен', 'завершён')"
        # Cancelled: support both 'отменен' and 'отменён' (with ё)
        cancelled_status_condition = "lower(trim(status)) IN ('отменен', 'отменён')"
        
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
        
        # Доп. расходы (пока = 0, зарезервировано для будущего использования)
        extra_expenses = 0.0
        
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
            
            prev_params = {
                "user_id": str(user_id),
                "prev_date_from": prev_date_from.isoformat(),
                "prev_date_to": prev_date_to.isoformat(),
                "shop_id": shop_id,  # Always include, can be None
            }
            
            prev_where = ["user_id = CAST(:user_id AS uuid)"]
            prev_where.append("date_created >= CAST(:prev_date_from AS date)")
            prev_where.append("date_created < CAST(:prev_date_to AS date) + INTERVAL '1 day'")
            prev_where.append("(:shop_id IS NULL OR shop_id = CAST(:shop_id AS uuid))")
            
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
        
        # E) Cumulative revenue (YTD - Year To Date, from start of year relative to date_to)
        # Does NOT depend on period, only on date_to (data_end_date)
        # year_start = date_trunc('year', date_to::timestamp)::date
        year_start = datetime(date_to_date.year, 1, 1).date()
        year_start_iso = year_start.isoformat()
        
        cumulative_where = [
            "user_id = CAST(:user_id AS uuid)",
            f"({completed_condition})",
            "date_created >= CAST(:year_start AS date)",
            "date_created < CAST(:date_to AS date) + INTERVAL '1 day'",
            "(:shop_id IS NULL OR shop_id = CAST(:shop_id AS uuid))"
        ]
        
        cumulative_where_clause = " AND ".join(cumulative_where)
        
        # Prepare params for cumulative query - MUST include date_to
        cumulative_params = {**params_base, "year_start": year_start_iso}
        
        cumulative_query = text(f"""
            SELECT COALESCE(SUM(revenue_sum), 0)
            FROM {qname("fact_sales")}
            WHERE {cumulative_where_clause}
        """)
        
        cumulative_result = db.execute(cumulative_query, cumulative_params)
        cumulative_revenue = float(cumulative_result.scalar() or 0)
        
        logger.info(f"cumulativeRevenue: year={date_to_date.year}, year_start={year_start_iso}, date_to={date_to_iso}, value={cumulative_revenue}")
        
        # F) STOCK aggregation (не зависит от period, только от user_id и shop_id)
        # Используем fact_leftout_snapshot.in_sale (В продаже, шт) для расчета остатков
        # A) Получить текущий loaded_at (max по user_id и опционально shop_id)
        stock_params = {
            "user_id": str(user_id),
            "shop_id": shop_id  # Can be None
        }
        
        max_loaded_query = text(f"""
            SELECT MAX(loaded_at) AS snap_loaded_at
            FROM {qname("fact_leftout_snapshot")}
            WHERE user_id = CAST(:user_id AS uuid)
                AND (:shop_id IS NULL OR shop_id = CAST(:shop_id AS uuid))
        """)
        
        max_loaded_result = db.execute(max_loaded_query, stock_params)
        snap_loaded_at = max_loaded_result.scalar()
        
        # Инициализация значений по умолчанию
        stock_quantity = 0.0
        stock_cost = 0.0
        stock_retail_price = 0.0
        stock_sku_total = 0
        stock_sku_with_stock = 0
        stock_snapshot_at = None
        stock_is_zero = False
        stock_zero_reason = None
        
        if snap_loaded_at:
            # B) По этому loaded_at посчитать агрегаты склада и цены по SKU/barcode
            stock_params["snap_loaded_at"] = snap_loaded_at
            
            # ТЗ Блок Склад:
            # 1) Товар на складе = left-out-report: SUM(В продаже, шт)
            #    Реализовано: SUM(in_sale) из fact_leftout_snapshot
            # 2) Себестоимость товара (на складе), сум = SUM(В продаже, шт * unit_cogs)
            #    Где: unit_cogs = SUM(cogs_sum)/NULLIF(SUM(qty),0) из fact_sales (завершенные заказы)
            #    Окно: фиксированное - последние 90 дней (НЕ зависит от period)
            # 3) Розничная цена товара (остатки), сум = SUM(В продаже, шт * unit_price)
            #    Где: unit_price = SUM(price_sum)/NULLIF(SUM(qty),0) из fact_sales (завершенные заказы)
            #    Окно: фиксированное - последние 90 дней (НЕ зависит от period)
            
            # Для расчета себестоимости используем фильтр shop из основного запроса
            # ВАЖНО: stock_cost НЕ зависит от period - всегда используем фиксированное окно последних 90 дней
            # Это обеспечивает стабильность метрики "Себест. тов. на складе, сум" независимо от выбранного периода
            stock_params.update(params_base)
            
            # Фиксированное окно для расчета unit_cogs: последние 90 дней от data_end_date
            # Это окно НЕ зависит от параметра period запроса пользователя
            unit_cogs_date_from_date = date_to_date - timedelta(days=89)
            unit_cogs_date_from = unit_cogs_date_from_date.isoformat()
            unit_cogs_date_to = date_to_iso
            
            stock_params["unit_cogs_date_from"] = unit_cogs_date_from
            stock_params["unit_cogs_date_to"] = unit_cogs_date_to
            
            stock_cogs_where = ["user_id = CAST(:user_id AS uuid)", f"({completed_condition})"]
            stock_cogs_where.append("(:shop_id IS NULL OR shop_id = CAST(:shop_id AS uuid))")
            stock_cogs_where.append("date_created >= CAST(:unit_cogs_date_from AS date)")
            stock_cogs_where.append("date_created < CAST(:unit_cogs_date_to AS date) + INTERVAL '1 day'")
            
            stock_cogs_where_clause = " AND ".join(stock_cogs_where)
            
            stock_query = text(f"""
                WITH snap AS (
                    -- Текущий snapshot склада из fact_leftout_snapshot
                    -- ТЗ: Товар на складе = sum(В продаже, шт) из left-out-report
                    SELECT
                        NULLIF(TRIM(sku), '') AS sku,
                        NULLIF(TRIM(barcode), '') AS barcode,
                        COALESCE(in_sale, 0) AS stock_qty,
                        MAX(loaded_at) AS stock_snapshot_at
                    FROM {qname("fact_leftout_snapshot")}
                    WHERE user_id = CAST(:user_id AS uuid)
                        AND (:shop_id IS NULL OR shop_id = CAST(:shop_id AS uuid))
                        AND loaded_at = CAST(:snap_loaded_at AS timestamp)
                    GROUP BY NULLIF(TRIM(sku), ''), NULLIF(TRIM(barcode), ''), COALESCE(in_sale, 0)
                ),
                unit_cogs_by_product AS (
                    -- ТЗ: unit_cogs = единичная себестоимость из sells_report
                    -- В fact_sales cogs_sum хранится как итоговая себестоимость по строке (total), поэтому:
                    -- unit_cogs = SUM(cogs_sum) / NULLIF(SUM(qty), 0)
                    -- Статус: lower(trim(status)) IN ('завершен', 'завершён')
                    -- Окно: фиксированное - последние 90 дней от data_end_date (НЕ зависит от period фильтра)
                    -- Это обеспечивает стабильность stock_cost независимо от выбранного периода
                    SELECT
                        NULLIF(TRIM(sku), '') AS sku,
                        NULLIF(TRIM(barcode), '') AS barcode,
                        COALESCE(
                            SUM(cogs_sum) / NULLIF(SUM(qty), 0),
                            0
                        ) AS unit_cogs
                    FROM {qname("fact_sales")}
                    WHERE {stock_cogs_where_clause}
                    GROUP BY NULLIF(TRIM(sku), ''), NULLIF(TRIM(barcode), '')
                ),
                unit_price_by_product AS (
                    -- ТЗ: unit_price = единичная цена из sells_report
                    -- В fact_sales price_sum хранится как итоговая цена по строке (total), поэтому:
                    -- unit_price = SUM(price_sum) / NULLIF(SUM(qty), 0)
                    -- Статус: lower(trim(status)) IN ('завершен', 'завершён')
                    -- Окно: фиксированное - последние 90 дней от data_end_date (НЕ зависит от period фильтра)
                    -- Это обеспечивает стабильность stock_retail_price независимо от выбранного периода
                    SELECT
                        NULLIF(TRIM(sku), '') AS sku,
                        NULLIF(TRIM(barcode), '') AS barcode,
                        COALESCE(
                            SUM(price_sum) / NULLIF(SUM(qty), 0),
                            0
                        ) AS unit_price
                    FROM {qname("fact_sales")}
                    WHERE {stock_cogs_where_clause}
                    GROUP BY NULLIF(TRIM(sku), ''), NULLIF(TRIM(barcode), '')
                ),
                stock_with_cogs AS (
                    -- Сопоставление товаров из snap с unit_cogs и unit_price по SKU и/или barcode
                    -- Приоритет: сначала по SKU, затем по barcode
                    SELECT
                        s.sku,
                        s.barcode,
                        s.stock_qty,
                        s.stock_snapshot_at AS stock_snapshot_at,
                        COALESCE(
                            -- Приоритет 1: сопоставление по SKU
                            uc_sku.unit_cogs,
                            -- Приоритет 2: сопоставление по barcode
                            uc_barcode.unit_cogs,
                            -- Если не найдено: 0
                            0
                        ) AS unit_cogs,
                        COALESCE(
                            -- Приоритет 1: сопоставление по SKU
                            up_sku.unit_price,
                            -- Приоритет 2: сопоставление по barcode
                            up_barcode.unit_price,
                            -- Если не найдено: 0
                            0
                        ) AS unit_price
                    FROM snap s
                    LEFT JOIN unit_cogs_by_product uc_sku ON (
                        uc_sku.sku = s.sku 
                        AND s.sku IS NOT NULL 
                        AND uc_sku.sku IS NOT NULL
                    )
                    LEFT JOIN unit_cogs_by_product uc_barcode ON (
                        uc_barcode.barcode = s.barcode 
                        AND s.barcode IS NOT NULL 
                        AND uc_barcode.barcode IS NOT NULL
                        AND uc_sku.unit_cogs IS NULL  -- Используем barcode только если не нашли по SKU
                    )
                    LEFT JOIN unit_price_by_product up_sku ON (
                        up_sku.sku = s.sku 
                        AND s.sku IS NOT NULL 
                        AND up_sku.sku IS NOT NULL
                    )
                    LEFT JOIN unit_price_by_product up_barcode ON (
                        up_barcode.barcode = s.barcode 
                        AND s.barcode IS NOT NULL 
                        AND up_barcode.barcode IS NOT NULL
                        AND up_sku.unit_price IS NULL  -- Используем barcode только если не нашли по SKU
                    )
                )
                SELECT
                    COUNT(*) AS stock_sku_total,
                    SUM(s.stock_qty) AS stock_quantity,
                    SUM(CASE WHEN s.stock_qty > 0 THEN 1 ELSE 0 END) AS stock_sku_with_stock,
                    MAX(s.stock_snapshot_at) AS stock_snapshot_at,
                    -- ТЗ: Розничная цена товара (остатки), сум = left-out-report: SUM(В продаже, шт * unit_price)
                    -- Где: stock_qty из left-out-report (in_sale), unit_price из sells_report (SUM(price_sum)/NULLIF(SUM(qty),0))
                    COALESCE(SUM(s.stock_qty * s.unit_price), 0) AS stock_retail_price,
                    -- ТЗ: Себестоимость товара (на складе), сум = SUM(stock_qty * unit_cogs)
                    -- Где: stock_qty из left-out-report (in_sale), unit_cogs из sells_report (SUM(cogs_sum)/NULLIF(SUM(qty),0))
                    COALESCE(SUM(s.stock_qty * s.unit_cogs), 0) AS stock_cost
                FROM stock_with_cogs s
            """)
            
            stock_result = db.execute(stock_query, stock_params)
            stock_row = stock_result.fetchone()
            
            if stock_row:
                stock_sku_total = int(stock_row[0] or 0)
                stock_quantity = float(stock_row[1] or 0)
                stock_sku_with_stock = int(stock_row[2] or 0)
                stock_snapshot_at = stock_row[3]
                stock_retail_price = float(stock_row[4] or 0)
                stock_cost = float(stock_row[5] or 0)
                
                # Smoke test: проверка что stock_retail_price не NULL (должно быть число, даже если 0)
                if stock_retail_price is None:
                    logger.warning(f"stock_retail_price is NULL for user_id={user_id}, shop_id={shop_id}, snap_loaded_at={snap_loaded_at}")
                    stock_retail_price = 0.0
                
                # D) stockIsZero / stockZeroReason
                if stock_sku_total == 0:
                    stock_is_zero = True
                    stock_zero_reason = "no_snapshot_data"
                elif stock_sku_with_stock == 0:
                    stock_is_zero = True
                    stock_zero_reason = "all_zero_in_snapshot"
                else:
                    stock_is_zero = False
                    stock_zero_reason = None
        else:
            # Нет snapshot данных
            stock_is_zero = True
            stock_zero_reason = "no_snapshot_data"
        
        # Smoke test: проверка что stock_retail_price корректно рассчитан (не NULL)
        if stock_retail_price is None:
            logger.error(f"CRITICAL: stock_retail_price is NULL after calculation for user_id={user_id}, shop_id={shop_id}")
            stock_retail_price = 0.0
        
        logger.info(f"stock: quantity={stock_quantity}, cost={stock_cost} (SUM(stock_qty * unit_cogs) по товарам), retail_price={stock_retail_price}, sku_total={stock_sku_total}, sku_with_stock={stock_sku_with_stock}, is_zero={stock_is_zero}, reason={stock_zero_reason}, snapshot_at={stock_snapshot_at}, shop_id={shop_id}, period={period_code}")
        
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
        
        # A) Определить snap_loaded_at (самый свежий snapshot до date_to, НЕ ограничивать >= date_from)
        # Используем fact_leftout_snapshot как единый источник склада
        snap_loaded_at_query = text(f"""
            SELECT MAX(loaded_at) AS snap_loaded_at
            FROM {qname("fact_leftout_snapshot")}
            WHERE user_id = CAST(:user_id AS uuid)
                AND (:shop_id IS NULL OR shop_id = CAST(:shop_id AS uuid))
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
                    SELECT
                        NULLIF(TRIM(sku), '') AS sku,
                        NULLIF(TRIM(barcode), '') AS barcode,
                        SUM(qty) AS qty_period,
                        SUM(revenue_sum) AS rev_period
                    FROM {qname("fact_sales")}
                    WHERE user_id = CAST(:user_id AS uuid)
                        AND ({completed_condition})
                        AND (:shop_id IS NULL OR shop_id = CAST(:shop_id AS uuid))
                        AND date_created >= CAST(:date_from_for_avg AS date)
                        AND date_created < CAST(:date_to AS date) + INTERVAL '1 day'
                    GROUP BY NULLIF(TRIM(sku), ''), NULLIF(TRIM(barcode), '')
                ),
                price_window AS (
                    -- Weighted average price из окна для расчета цены (только завершенные заказы)
                    -- Если period=all, используем последние 90 дней (зафиксировано в комментарии)
                    SELECT
                        NULLIF(TRIM(sku), '') AS sku,
                        NULLIF(TRIM(barcode), '') AS barcode,
                        SUM(revenue_sum) AS rev_window,
                        SUM(qty) AS qty_window
                    FROM {qname("fact_sales")}
                    WHERE user_id = CAST(:user_id AS uuid)
                        AND ({completed_condition})
                        AND (:shop_id IS NULL OR shop_id = CAST(:shop_id AS uuid))
                        AND date_created >= CAST(:price_window_from AS date)
                        AND date_created < CAST(:date_to AS date) + INTERVAL '1 day'
                    GROUP BY NULLIF(TRIM(sku), ''), NULLIF(TRIM(barcode), '')
                ),
                snap AS (
                    -- Текущий snapshot склада из fact_leftout_snapshot
                    -- Остатки FBO = in_sale + sdh_stock (всего в продаже и на СДХ)
                    SELECT
                        NULLIF(TRIM(sku), '') AS sku,
                        NULLIF(TRIM(barcode), '') AS barcode,
                        COALESCE(in_sale, 0) + COALESCE(sdh_stock, 0) AS stock_fbo
                    FROM {qname("fact_leftout_snapshot")}
                    WHERE user_id = CAST(:user_id AS uuid)
                        AND (:shop_id IS NULL OR shop_id = CAST(:shop_id AS uuid))
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
                        s.barcode,
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
                        (ps.sku = s.sku AND s.sku IS NOT NULL AND ps.sku IS NOT NULL)
                        OR (ps.barcode = s.barcode AND s.barcode IS NOT NULL AND ps.barcode IS NOT NULL)
                    )
                    LEFT JOIN price_window pw ON (
                        (pw.sku = s.sku AND s.sku IS NOT NULL AND pw.sku IS NOT NULL)
                        OR (pw.barcode = s.barcode AND s.barcode IS NOT NULL AND pw.barcode IS NOT NULL)
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
            "stockQuantity": stock_quantity,
            "stockCost": stock_cost,
            "stockRetailPrice": stock_retail_price,
            "stockSkuTotal": stock_sku_total,
            "stockSkuWithStock": stock_sku_with_stock,
            "stockSnapshotAt": stock_snapshot_at.isoformat() if stock_snapshot_at and hasattr(stock_snapshot_at, 'isoformat') else (str(stock_snapshot_at) if stock_snapshot_at else None),
            "stockIsZero": stock_is_zero,
            "stockZeroReason": stock_zero_reason,
            "period_range": period_range_dict
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in kpi_summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
