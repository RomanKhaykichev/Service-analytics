from fastapi import APIRouter, Request, HTTPException, Query
from decimal import Decimal
from app.auth import get_user_id
from app.db import execute_one, execute_all
from app.schemas import KPIGlobalResponse, KPIFilteredResponse, PeriodInfo, Filters, SalesMetrics, FinanceMetrics
from app.utils import parse_period, normalize_shop_id

router = APIRouter()


@router.get("/kpi/global", response_model=KPIGlobalResponse)
async def get_kpi_global(request: Request):
    """Get global YTD revenue KPI."""
    user_id = get_user_id(request)
    
    query = """
        SELECT COALESCE(revenue_ytd, 0) AS revenue_ytd
        FROM app.v_kpi_global_ytd
        WHERE user_id = %(user_id)s
    """
    
    row = execute_one(query, {"user_id": user_id})
    revenue_ytd = float(row["revenue_ytd"]) if row else 0.0
    
    return KPIGlobalResponse(revenue_ytd=revenue_ytd)


@router.get("/kpi", response_model=KPIFilteredResponse)
async def get_kpi(
    request: Request,
    period: str = Query(default="30d", regex="^(7d|30d|60d|90d|all)$"),
    shop_id: str = Query(default=None)
):
    """Get filtered KPI metrics."""
    user_id = get_user_id(request)
    
    try:
        date_from, date_to, code = parse_period(period)
        shop_id_normalized = normalize_shop_id(shop_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    query = """
        SELECT
          COALESCE(sum(orders_cnt), 0) AS orders_cnt,
          COALESCE(sum(qty), 0) AS qty,
          COALESCE(sum(returns_qty), 0) AS returns_qty,
          COALESCE(sum(revenue_sum), 0) AS revenue_sum,
          COALESCE(sum(commission_sum), 0) AS commission_sum,
          COALESCE(sum(logistics_sum), 0) AS logistics_sum,
          COALESCE(sum(promo_sum), 0) AS promo_sum,
          COALESCE(sum(cogs_sum), 0) AS cogs_sum,
          COALESCE(sum(profit_sum), 0) AS profit_sum
        FROM app.v_kpi_filtered_daily
        WHERE user_id = %(user_id)s
          AND (shop_id = COALESCE(CAST(%(shop_id)s AS uuid), shop_id))
          AND day BETWEEN %(date_from)s AND %(date_to)s
    """
    
    row = execute_one(query, {
        "user_id": user_id,
        "shop_id": shop_id_normalized,
        "date_from": date_from,
        "date_to": date_to
    })
    
    if not row:
        # Return zeros if no data
        row = {
            "orders_cnt": 0,
            "qty": 0,
            "returns_qty": 0,
            "revenue_sum": 0,
            "commission_sum": 0,
            "logistics_sum": 0,
            "promo_sum": 0,
            "cogs_sum": 0,
            "profit_sum": 0
        }
    
    orders_cnt = int(row["orders_cnt"])
    qty = int(row["qty"])
    returns_qty = int(row["returns_qty"])
    revenue_sum = float(row["revenue_sum"])
    commission_sum = float(row["commission_sum"])
    logistics_sum = float(row["logistics_sum"])
    promo_sum = float(row["promo_sum"])
    cogs_sum = float(row["cogs_sum"])
    profit_sum = float(row["profit_sum"])
    
    # Calculate derived metrics
    buyouts_qty = qty - returns_qty
    buyout_ratio = buyouts_qty / qty if qty > 0 else None
    expenses_sum = commission_sum + logistics_sum + promo_sum + cogs_sum
    avg_check = revenue_sum / orders_cnt if orders_cnt > 0 else None
    margin_ratio = profit_sum / revenue_sum if revenue_sum > 0 else None
    
    return KPIFilteredResponse(
        period=PeriodInfo(
            code=code,
            date_from=date_from.isoformat(),
            date_to=date_to.isoformat()
        ),
        filters=Filters(shop_id=shop_id_normalized),
        sales=SalesMetrics(
            orders_cnt=orders_cnt,
            qty=qty,
            returns_qty=returns_qty,
            buyouts_qty=buyouts_qty,
            buyout_ratio=buyout_ratio,
            avg_check=avg_check
        ),
        finance=FinanceMetrics(
            revenue_sum=revenue_sum,
            expenses_sum=expenses_sum,
            profit_sum=profit_sum,
            margin_ratio=margin_ratio
        )
    )
