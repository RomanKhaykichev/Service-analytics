from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta
import logging
import re
from app.db import get_db, qname
from app.deps import require_user
from app.utils.statuses import get_status_sql_condition
from app.utils.barcode import barcode_norm_sql
from app.utils.metrics import get_status_conditions
from app.settings import get_settings
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


@router.get("/kpi/summary")
def kpi_summary(
    period: str = "30d",
    shop_id: Optional[str] = None,
    shop: Optional[str] = Query(default=None, description="Shop name (string) for seller-storage filtering"),
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Get KPI summary metrics.
    
    Filtering:
    - shop_id (UUID): for sales/expenses/warehouse metrics (from dim_shop)
    - shop (string): for seller-storage metrics (from stg_storage.shop_raw)
    
    If both provided, shop_id is used for non-storage metrics, shop for storage metrics.
    """
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
    
    # Нормализуем shop для seller-storage фильтрации
    shop_norm = None
    if shop:
        shop_norm = shop.upper().strip()
        shop_norm = re.sub(r'\s+', ' ', shop_norm)  # normalize whitespace
    
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
        
        # Sales shop filter: by storage barcodes (shop_norm) or by shop_id (UUID)
        # When shop_norm: only rows whose barcode_norm exists in fact_storage_snapshot for that shop
        sales_shop_filter = ""
        if shop_norm:
            sales_shop_filter = f"""EXISTS (
                SELECT 1 FROM {qname("fact_storage_snapshot")} fss
                WHERE fss.user_id = fact_sales.user_id
                  AND COALESCE(fss.barcode_norm, {barcode_norm_sql('fss.barcode')}) = COALESCE(fact_sales.barcode_norm, {barcode_norm_sql('fact_sales.barcode')})
                  AND upper(regexp_replace(trim(COALESCE(fss.shop_raw, '')), '\\s+', ' ', 'g')) = :shop_norm
            )"""
        elif shop_id:
            sales_shop_filter = "(:shop_id IS NULL OR shop_id = CAST(:shop_id AS uuid))"
        
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
        
        # Доп. расходы: SUM(Доп. расходы[Сумма]) из manual_expenses
        # Фильтры: период (expense_date), магазин (shop_id), user_id, is_deleted = false
        # ТЗ: Доп. расходы = SUM(Доп. расходы[Сумма])
        # Условия: учитывать выбранный период (по полю «Дата»), магазин (если выбран), удалённые записи не учитывать
        
        # DEBUG: Логируем параметры периода ПЕРЕД расчетом
        logger.info(f"[DEBUG] extra_expenses BEFORE calculation: period={period_code}, date_from={date_from_iso or 'NULL'}, date_to={date_to_iso}, shop_id={shop_id}, user_id={user_id}")
        
        # Prepare params for manual expenses query - используем те же date_from/date_to, что и для остальных KPI
        manual_expenses_params = {**params_base}
        
        # Проверяем схему таблицы manual_expenses: наличие колонок shop_id и shop_name
        check_schema_query = text(f"""
            SELECT 
                EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_schema = :schema 
                      AND table_name = 'manual_expenses' 
                      AND column_name = 'shop_id'
                ) AS has_shop_id,
                EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_schema = :schema 
                      AND table_name = 'manual_expenses' 
                      AND column_name = 'shop_name'
                ) AS has_shop_name
        """)
        schema_result = db.execute(check_schema_query, {"schema": settings.DB_SCHEMA})
        schema_row = schema_result.fetchone()
        has_shop_id_column = schema_row[0] if schema_row else False
        has_shop_name_column = schema_row[1] if schema_row else False
        
        logger.info(f"[DEBUG] manual_expenses schema check: has_shop_id={has_shop_id_column}, has_shop_name={has_shop_name_column}")
        
        # Формируем фильтр по магазину (безопасно, проверяя наличие колонок)
        shop_filter = ""
        if shop_id:
            if has_shop_id_column:
                # Если shop_id существует - фильтруем по shop_id
                shop_filter = "AND e.shop_id = CAST(:shop_id AS uuid)"
                logger.info(f"[DEBUG] Applying shop_id filter: shop_id={shop_id}")
            elif has_shop_name_column:
                # Если shop_name существует - фильтруем через JOIN с dim_shop
                # Сначала получаем shop_name из dim_shop по shop_id
                shop_name_query = text(f"""
                    SELECT shop_name 
                    FROM {qname("dim_shop")} 
                    WHERE shop_id = CAST(:shop_id AS uuid) AND user_id = CAST(:user_id AS uuid)
                """)
                shop_name_result = db.execute(shop_name_query, {"shop_id": shop_id, "user_id": str(user_id)})
                shop_name_row = shop_name_result.fetchone()
                if shop_name_row and shop_name_row[0]:
                    shop_name = shop_name_row[0]
                    shop_filter = f"AND e.shop_name = '{shop_name}'"
                    logger.info(f"[DEBUG] Applying shop_name filter: shop_name={shop_name}")
                else:
                    logger.warning(f"[DEBUG] shop_id={shop_id} not found in dim_shop, skipping shop filter")
            else:
                # Колонок shop_id и shop_name нет - не применяем фильтр
                logger.info(f"[DEBUG] No shop_id or shop_name columns found, skipping shop filter")
        else:
            logger.info(f"[DEBUG] shop_id is NULL (all shops), skipping shop filter")
        
        # Формируем фильтр по дате - используем те же date_from/date_to, что и для остальных KPI
        # Период применяется по expense_date: WHERE expense_date >= :date_from AND expense_date <= :date_to
        date_from_filter = ""
        if date_from:
            manual_expenses_params["date_from"] = date_from.isoformat()
            date_from_filter = "AND e.expense_date >= CAST(:date_from AS date)"
            logger.info(f"[DEBUG] Applying date_from filter: date_from={date_from.isoformat()}")
        else:
            logger.info(f"[DEBUG] date_from is NULL (period=all), no date_from filter")
        
        logger.info(f"[DEBUG] Applying date_to filter: date_to={date_to_iso}")
        
        # SQL-запрос: период применяется по expense_date
        manual_expenses_query = text(f"""
            SELECT 
                COALESCE(SUM(e.amount_sum), 0) AS extra_sum
            FROM {qname("manual_expenses")} e
            WHERE e.user_id = CAST(:user_id AS uuid)
              AND e.is_deleted = false
              {date_from_filter}
              AND e.expense_date <= CAST(:date_to AS date)
              {shop_filter}
        """)
        
        # Debug: считаем количество записей в периоде
        count_query = text(f"""
            SELECT COUNT(*) 
            FROM {qname("manual_expenses")} e
            WHERE e.user_id = CAST(:user_id AS uuid)
              AND e.is_deleted = false
              {date_from_filter}
              AND e.expense_date <= CAST(:date_to AS date)
              {shop_filter}
        """)
        
        logger.info(f"[DEBUG] Executing manual_expenses query with params: {manual_expenses_params}")
        # Логируем SQL-запрос для отладки (без f-string, так как это уже text объект)
        logger.info(f"[DEBUG] Query filters: date_from_filter='{date_from_filter}', shop_filter='{shop_filter}'")
        
        manual_expenses_result = db.execute(manual_expenses_query, manual_expenses_params)
        manual_expenses_row = manual_expenses_result.fetchone()
        
        count_result = db.execute(count_query, manual_expenses_params)
        count_row = count_result.fetchone()
        expenses_count = int(count_row[0] or 0) if count_row else 0
        
        extra_expenses = float(manual_expenses_row[0] or 0) if manual_expenses_row else 0.0
        
        # DEBUG: Логируем результат ПОСЛЕ расчета
        logger.info(f"[DEBUG] extra_expenses AFTER calculation: expenses_count={expenses_count}, extra_expenses={extra_expenses}, period_filter=[date_from={date_from_iso or 'NULL'}, date_to={date_to_iso}], shop_id={shop_id}")
        
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
        ]
        if sales_shop_filter:
            cumulative_where.append(sales_shop_filter)
        
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
        
        # F) STOCK aggregation (не зависит от period, только от user_id и shop_id/shop)
        # Используем fact_leftout_snapshot.in_sale (В продаже, шт) для расчета остатков
        # A) Получить текущий loaded_at (max по user_id и опционально shop_id или shop)
        stock_params = {
            "user_id": str(user_id),
            "shop_id": shop_id,  # Can be None (UUID для leftout)
            "shop_norm": shop_norm  # Can be None (string для seller-storage)
        }
        
        # Фильтр для leftout: если передан shop (seller-storage) - фильтруем через JOIN с fact_storage_snapshot
        # Если передан shop_id (UUID) - фильтруем напрямую по shop_id
        # Для max_loaded_query используем упрощённый фильтр (без EXISTS, т.к. нужен только MAX)
        leftout_max_filter = ""
        if shop_norm:
            # Фильтр по seller-storage: только товары (barcode_norm), присутствующие в выбранном магазине storage.
            # Связь по barcode_norm; shop_raw — колонка «Магазин»; сравнение с upper(normalize(shop_raw)).
            leftout_max_filter = f"""
                AND EXISTS (
                    SELECT 1 
                    FROM {qname("fact_storage_snapshot")} fss
                    WHERE fss.user_id = CAST(:user_id AS uuid)
                        AND COALESCE(fss.barcode_norm, {barcode_norm_sql('fss.barcode')}) = COALESCE(fact_leftout_snapshot.barcode_norm, {barcode_norm_sql('fact_leftout_snapshot.barcode')})
                        AND upper(regexp_replace(trim(COALESCE(fss.shop_raw, '')), '\\s+', ' ', 'g')) = :shop_norm
                )
            """
        elif shop_id:
            leftout_max_filter = "AND (:shop_id IS NULL OR shop_id = CAST(:shop_id AS uuid))"
        
        max_loaded_query = text(f"""
            SELECT MAX(loaded_at) AS snap_loaded_at
            FROM {qname("fact_leftout_snapshot")}
            WHERE user_id = CAST(:user_id AS uuid)
                {leftout_max_filter}
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
            # 2) Себест. тов. на складе, сум = СУММА(left-out-report[В продаже, шт] * sells_report[Себестоимость (сумы) ДЛЯ ЭТОГО ШТРИХКОДА НА ПОСЛЕДНЮЮ ДАТУ])
            #    JOIN по штрихкоду, построчное умножение, затем суммирование
            #    Источники: left-out-report → fact_leftout_snapshot (in_sale), sells_report → fact_sales (cogs_sum)
            #    Окно для fact_sales: только последняя дата (MAX(date_created)) в рамках текущих фильтров (period/shop)
            #    NULL/пустые значения трактуются как 0 (COALESCE)
            # 3) Рознич. цена тов., сум = СУММА(left-out-report[В продаже, шт] * sells_report[Цена (сумы) ДЛЯ ЭТОГО ШТРИХКОДА НА ПОСЛЕДНЮЮ ДАТУ])
            #    JOIN по штрихкоду, построчное умножение, затем суммирование
            #    Источники: left-out-report → fact_leftout_snapshot (in_sale), sells_report → fact_sales (price_sum)
            #    Окно для fact_sales: только последняя дата (MAX(date_created)) в рамках текущих фильтров (period/shop)
            #    NULL/пустые значения трактуются как 0 (COALESCE)
            
            # Для расчета используем те же фильтры, что и для основного запроса sales (period, shop_id)
            stock_params.update(params_base)
            if date_from:
                stock_params["date_from"] = date_from.isoformat()
            
            # Фильтры для fact_sales (те же, что и для основного запроса: period + shop)
            stock_sales_where = ["user_id = CAST(:user_id AS uuid)", f"({completed_condition})"]
            if sales_shop_filter:
                stock_sales_where.append(sales_shop_filter)
            if date_from:
                stock_sales_where.append("date_created >= CAST(:date_from AS date)")
            stock_sales_where.append("date_created < CAST(:date_to AS date) + INTERVAL '1 day'")
            
            stock_sales_where_clause = " AND ".join(stock_sales_where)
            
            # Формируем фильтр для snap CTE (тот же, что и для max_loaded_query)
            snap_filter = leftout_max_filter
            
            stock_query = text(f"""
                WITH snap AS (
                    -- Текущий snapshot склада из fact_leftout_snapshot
                    -- ТЗ: Товар на складе = sum(В продаже, шт) из left-out-report
                    -- barcode_norm вычисляется на лету: нормализация barcode (удаление пробелов)
                    SELECT
                        NULLIF(TRIM(sku), '') AS sku,
                        {barcode_norm_sql('barcode')} AS barcode_norm,
                        COALESCE(in_sale, 0) AS stock_qty,
                        MAX(loaded_at) AS stock_snapshot_at
                    FROM {qname("fact_leftout_snapshot")}
                    WHERE user_id = CAST(:user_id AS uuid)
                        {snap_filter}
                        AND loaded_at = CAST(:snap_loaded_at AS timestamp)
                    GROUP BY NULLIF(TRIM(sku), ''), {barcode_norm_sql('barcode')}, COALESCE(in_sale, 0)
                ),
                last_date AS (
                    -- Определяем последнюю (максимальную) дату из sells_report в рамках текущих фильтров
                    SELECT MAX(date_created)::date AS last_date
                    FROM {qname("fact_sales")}
                    WHERE {stock_sales_where_clause}
                ),
                sales_last AS (
                    -- sells_report_last: sells_report, отфильтрованный до last_date и агрегированный до 1 строки на «Штрихкод»
                    -- Статус: lower(trim(status)) IN ('завершен', 'завершён')
                    -- Для каждого штрихкода берем ровно одну строку на last_date
                    -- Если несколько строк на одну дату - агрегируем через MAX (берем максимальные значения)
                    -- Если last_date NULL (нет данных) - возвращаем пустой результат (все цены/себестоимости = 0)
                    -- barcode_norm вычисляется на лету: нормализация barcode (удаление пробелов)
                    SELECT
                        NULLIF(TRIM(sku), '') AS sku,
                        {barcode_norm_sql('barcode')} AS barcode_norm,
                        COALESCE(MAX(cogs_sum), 0) AS cogs_sum,
                        COALESCE(MAX(price_sum), 0) AS price_sum
                    FROM {qname("fact_sales")}
                    CROSS JOIN last_date ld
                    WHERE {stock_sales_where_clause}
                        AND ld.last_date IS NOT NULL
                        AND date_created::date = ld.last_date
                    GROUP BY NULLIF(TRIM(sku), ''), {barcode_norm_sql('barcode')}
                ),
                stock_with_sales AS (
                    -- Сопоставление товаров из snap с данными из sells_report на последнюю дату
                    -- Приоритет сопоставления: сначала по barcode_norm (если не NULL), затем по sku
                    SELECT
                        s.sku,
                        s.barcode_norm,
                        s.stock_qty,
                        s.stock_snapshot_at,
                        COALESCE(
                            -- Приоритет 1: сопоставление по barcode_norm
                            sales_barcode.cogs_sum,
                            -- Приоритет 2: сопоставление по SKU (fallback)
                            sales_sku.cogs_sum,
                            -- Если не найдено: 0
                            0
                        ) AS cogs_sum,
                        COALESCE(
                            -- Приоритет 1: сопоставление по barcode_norm
                            sales_barcode.price_sum,
                            -- Приоритет 2: сопоставление по SKU (fallback)
                            sales_sku.price_sum,
                            -- Если не найдено: 0
                            0
                        ) AS price_sum
                    FROM snap s
                    LEFT JOIN sales_last sales_barcode ON (
                        sales_barcode.barcode_norm = s.barcode_norm 
                        AND s.barcode_norm IS NOT NULL 
                        AND sales_barcode.barcode_norm IS NOT NULL
                    )
                    LEFT JOIN sales_last sales_sku ON (
                        sales_sku.sku = s.sku 
                        AND s.sku IS NOT NULL 
                        AND sales_sku.sku IS NOT NULL
                        AND sales_barcode.cogs_sum IS NULL  -- Используем sku только если не нашли по barcode_norm
                    )
                )
                SELECT
                    COUNT(*) AS stock_sku_total,
                    SUM(s.stock_qty) AS stock_quantity,
                    SUM(CASE WHEN s.stock_qty > 0 THEN 1 ELSE 0 END) AS stock_sku_with_stock,
                    MAX(s.stock_snapshot_at) AS stock_snapshot_at,
                    -- ТЗ: Рознич. цена тов., сум = СУММА(left-out-report[В продаже, шт] * sells_report_last[Цена (сумы)])
                    -- где sells_report_last — это sells_report, отфильтрованный до last_date и агрегированный до 1 строки на «Штрихкод»
                    -- JOIN по штрихкоду, построчное умножение, затем суммирование
                    -- NULL/пустые значения трактуются как 0 через COALESCE
                    COALESCE(SUM(COALESCE(s.stock_qty, 0) * COALESCE(s.price_sum, 0)), 0) AS stock_retail_price,
                    -- ТЗ: Себест. тов. на складе, сум = СУММА(left-out-report[В продаже, шт] * sells_report_last[Себестоимость (сумы)])
                    -- где sells_report_last — это sells_report, отфильтрованный до last_date и агрегированный до 1 строки на «Штрихкод»
                    -- JOIN по штрихкоду, построчное умножение, затем суммирование
                    -- NULL/пустые значения трактуются как 0 через COALESCE
                    COALESCE(SUM(COALESCE(s.stock_qty, 0) * COALESCE(s.cogs_sum, 0)), 0) AS stock_cost
                FROM stock_with_sales s
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
