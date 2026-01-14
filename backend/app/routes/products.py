from fastapi import APIRouter, Request, HTTPException, Query, Path
from typing import Optional
from app.auth import get_user_id
from app.db import execute_one, execute_all
from app.schemas import (
    ProductsResponse, ProductDetailResponse,
    PeriodInfo, Filters, Paging, ProductItem,
    ProductInfo, ProductSales, ProductFinance, ProductStock
)
from app.utils import parse_period, normalize_shop_id

router = APIRouter()


@router.get("/products", response_model=ProductsResponse)
async def get_products(
    request: Request,
    period: str = Query(default="30d", regex="^(7d|30d|60d|90d|all)$"),
    shop_id: str = Query(default=None),
    q: str = Query(default=None),
    sort: str = Query(default="revenue", regex="^(revenue|profit|returns|stock|turnover)$"),
    order: str = Query(default="desc", regex="^(asc|desc)$"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    include_zero_sales: int = Query(default=0, ge=0, le=1)
):
    """Get products list with sales and stock data."""
    user_id = get_user_id(request)
    
    try:
        date_from, date_to, code = parse_period(period)
        shop_id_normalized = normalize_shop_id(shop_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Build search condition
    search_cond = ""
    params = {
        "user_id": user_id,
        "shop_id": shop_id_normalized,
        "date_from": date_from,
        "date_to": date_to,
        "limit": limit,
        "offset": offset
    }
    
    if q:
        search_cond = """
          AND (
            product_name ILIKE %(q)s OR 
            sku ILIKE %(q)s OR 
            barcode ILIKE %(q)s
          )
        """
        params["q"] = f"%{q}%"
    
    # Build zero sales filter
    zero_sales_cond = ""
    if include_zero_sales == 0:
        zero_sales_cond = "HAVING SUM(orders_cnt) > 0 OR SUM(qty) > 0"
    
    # Build order by
    order_by_map = {
        "revenue": "COALESCE(agg.revenue_sum, 0)",
        "profit": "COALESCE(agg.profit_sum, 0)",
        "returns": "COALESCE(agg.returns_qty, 0)",
        "stock": "COALESCE(stock.stock_qty, 0)",
        "turnover": "CASE WHEN stock.turnover_days IS NULL THEN 999999 WHEN regexp_replace(trim(stock.turnover_days::text), ',', '.') ~ '^\\d+(\\.\\d+)?$' THEN regexp_replace(trim(stock.turnover_days::text), ',', '.')::numeric ELSE 999999 END"
    }
    order_by_expr = order_by_map.get(sort, order_by_map["revenue"])
    order_dir = "DESC" if order == "desc" else "ASC"
    
    # Main query with CTE - improved with fallback product_name
    query = f"""
        WITH sales_with_profit AS (
          SELECT
            shop_id,
            barcode,
            sku,
            MAX(product_name) AS product_name,
            MAX(category) AS category,
            SUM(orders_cnt) AS orders_cnt,
            SUM(qty) AS qty,
            SUM(returns_qty) AS returns_qty,
            SUM(revenue_sum) AS revenue_sum,
            SUM(commission_sum) AS commission_sum,
            SUM(logistics_sum) AS logistics_sum,
            SUM(promo_sum) AS promo_sum,
            SUM(cogs_sum) AS cogs_sum,
            (SUM(revenue_sum) - SUM(commission_sum) - SUM(logistics_sum) - SUM(promo_sum) - SUM(cogs_sum)) AS profit_sum
          FROM app.v_sales_daily
          WHERE user_id = %(user_id)s
            AND (shop_id = COALESCE(CAST(%(shop_id)s AS uuid), shop_id))
            AND day BETWEEN %(date_from)s AND %(date_to)s
            {search_cond}
          GROUP BY shop_id, barcode, sku
          {zero_sales_cond}
        ),
        agg AS (
          SELECT
            s.shop_id,
            s.barcode,
            s.sku,
            s.product_name,
            s.category,
            s.orders_cnt,
            s.qty,
            s.returns_qty,
            s.revenue_sum,
            s.profit_sum,
            CASE 
              WHEN s.revenue_sum > 0 THEN s.profit_sum / s.revenue_sum 
              ELSE NULL 
            END AS margin_ratio
          FROM sales_with_profit s
        )
        SELECT
          agg.*,
          stock.product_name AS stock_product_name,
          -- Safe cast for numeric fields (handle NULL and ensure numeric type)
          -- View v_product_current_stock already handles safe casting, but add extra safety here
          stock.stock_qty,
          stock.coverage_days,
          CASE 
            WHEN stock.turnover_days IS NULL THEN NULL
            WHEN regexp_replace(trim(stock.turnover_days::text), ',', '.') ~ '^\\d+(\\.\\d+)?$' THEN regexp_replace(trim(stock.turnover_days::text), ',', '.')::numeric
            ELSE NULL
          END AS turnover_days,
          COUNT(*) OVER() AS total
        FROM agg
        LEFT JOIN app.v_product_current_stock stock
          ON stock.user_id = %(user_id)s
         AND stock.shop_id = agg.shop_id
         AND stock.barcode = agg.barcode
        ORDER BY {order_by_expr} {order_dir}
        LIMIT %(limit)s OFFSET %(offset)s
    """
    
    rows = execute_all(query, params)
    
    # Get total count
    total = int(rows[0]["total"]) if rows else 0
    
    items = []
    for row in rows:
        revenue_sum = float(row["revenue_sum"]) if row["revenue_sum"] else 0.0
        profit_sum = float(row["profit_sum"]) if row["profit_sum"] else 0.0
        
        # Fallback product_name: sales -> stock -> sku -> "Товар {barcode}"
        product_name = row.get("product_name")
        if not product_name:
            product_name = row.get("stock_product_name")
        if not product_name:
            sku_val = row.get("sku")
            if sku_val:
                product_name = sku_val
            else:
                product_name = f"Товар {row['barcode']}"
        
        items.append(ProductItem(
            barcode=row["barcode"],
            sku=row["sku"] or "",
            product_name=product_name,
            category=row["category"],
            orders_cnt=int(row["orders_cnt"]),
            qty=int(row["qty"]),
            returns_qty=int(row["returns_qty"]),
            revenue_sum=revenue_sum,
            profit_sum=profit_sum,
            margin_ratio=float(row["margin_ratio"]) if row["margin_ratio"] is not None else None,
            stock_qty=float(row["stock_qty"]) if row["stock_qty"] is not None else None,
            coverage_days=float(row["coverage_days"]) if row["coverage_days"] is not None else None,
            turnover_days=float(row["turnover_days"]) if row["turnover_days"] is not None else None
        ))
    
    return ProductsResponse(
        period=PeriodInfo(
            code=code,
            date_from=date_from.isoformat(),
            date_to=date_to.isoformat()
        ),
        filters=Filters(shop_id=shop_id_normalized, q=q),
        paging=Paging(limit=limit, offset=offset, total=total),
        items=items
    )


@router.get("/products/{barcode}", response_model=ProductDetailResponse)
async def get_product_detail(
    request: Request,
    barcode: str = Path(...),
    period: str = Query(default="30d", regex="^(7d|30d|60d|90d|all)$"),
    shop_id: str = Query(...)
):
    """Get product detail with sales, finance, stock and charts."""
    user_id = get_user_id(request)
    
    try:
        date_from, date_to, code = parse_period(period)
        shop_id_normalized = normalize_shop_id(shop_id)
        if shop_id_normalized is None:
            raise ValueError("shop_id is required for product detail")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    params = {
        "user_id": user_id,
        "shop_id": shop_id_normalized,
        "barcode": barcode,
        "date_from": date_from,
        "date_to": date_to
    }
    
    # A) Product header with fallback (sales -> stock -> sku -> "Товар {barcode}")
    query_product_sales = """
        SELECT
          barcode::text AS barcode,
          sku::text AS sku,
          product_name::text AS product_name,
          category::text AS category
        FROM app.v_sales_daily
        WHERE user_id = %(user_id)s
          AND shop_id = %(shop_id)s::uuid
          AND barcode = %(barcode)s
        ORDER BY day DESC
        LIMIT 1
    """
    
    row_product = execute_one(query_product_sales, params)
    
    product_name = None
    category = None
    sku = None
    
    if row_product:
        product_name = row_product.get("product_name")
        category = row_product.get("category")
        sku = row_product.get("sku")
    
    # Fallback to stock view if no name from sales
    if not product_name:
        query_product_stock = """
            SELECT
              barcode::text AS barcode,
              sku::text AS sku,
              product_name::text AS product_name
            FROM app.v_product_current_stock
            WHERE user_id = %(user_id)s
              AND shop_id = %(shop_id)s::uuid
              AND barcode = %(barcode)s
        """
        row_stock_header = execute_one(query_product_stock, params)
        if row_stock_header:
            if not product_name:
                product_name = row_stock_header.get("product_name")
            if not sku:
                sku = row_stock_header.get("sku")
    
    # Final fallback for name
    if not product_name:
        if sku:
            product_name = sku
        else:
            product_name = f"Товар {barcode}"
    
    # At least barcode must exist
    if not barcode:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product_info = ProductInfo(
        barcode=barcode,
        sku=sku or "",
        name=product_name,
        category=category
    )
    
    # B) Sales aggregates
    query_sales = """
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
        FROM app.v_product_detail_daily
        WHERE user_id = %(user_id)s
          AND shop_id = %(shop_id)s::uuid
          AND barcode = %(barcode)s
          AND day BETWEEN %(date_from)s AND %(date_to)s
    """
    
    row_sales = execute_one(query_sales, params)
    
    if not row_sales:
        row_sales = {
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
    
    orders_cnt = int(row_sales["orders_cnt"])
    qty = int(row_sales["qty"])
    returns_qty = int(row_sales["returns_qty"])
    revenue_sum = float(row_sales["revenue_sum"])
    commission_sum = float(row_sales["commission_sum"])
    logistics_sum = float(row_sales["logistics_sum"])
    promo_sum = float(row_sales["promo_sum"])
    cogs_sum = float(row_sales["cogs_sum"])
    profit_sum = float(row_sales["profit_sum"])
    
    buyouts_qty = qty - returns_qty
    buyout_ratio = buyouts_qty / qty if qty > 0 else None
    expenses_sum = commission_sum + logistics_sum + promo_sum + cogs_sum
    avg_check = revenue_sum / orders_cnt if orders_cnt > 0 else None
    margin_ratio = profit_sum / revenue_sum if revenue_sum > 0 else None
    
    product_sales = ProductSales(
        orders_cnt=orders_cnt,
        qty=qty,
        returns_qty=returns_qty,
        buyouts_qty=buyouts_qty,
        buyout_ratio=buyout_ratio,
        revenue_sum=revenue_sum,
        avg_check=avg_check
    )
    
    product_finance = ProductFinance(
        commission_sum=commission_sum,
        logistics_sum=logistics_sum,
        promo_sum=promo_sum,
        cogs_sum=cogs_sum,
        expenses_sum=expenses_sum,
        profit_sum=profit_sum,
        margin_ratio=margin_ratio
    )
    
    # C) Stock with parse error detection
    query_stock = """
        SELECT
          stock_qty,
          coverage_days,
          turnover_days,
          fee_total_30d,
          storage_type,
          size_group
        FROM app.v_product_current_stock
        WHERE user_id = %(user_id)s
          AND shop_id = %(shop_id)s::uuid
          AND barcode = %(barcode)s
    """
    
    row_stock = execute_one(query_stock, params)
    
    stock_parse_error = False
    if row_stock and row_stock.get("stock_qty") is None:
        stock_parse_error = True
    
    product_stock = ProductStock(
        stock_qty=float(row_stock["stock_qty"]) if row_stock and row_stock["stock_qty"] is not None else None,
        coverage_days=float(row_stock["coverage_days"]) if row_stock and row_stock["coverage_days"] is not None else None,
        turnover_days=float(row_stock["turnover_days"]) if row_stock and row_stock["turnover_days"] is not None else None,
        fee_total_30d=float(row_stock["fee_total_30d"]) if row_stock and row_stock["fee_total_30d"] is not None else None,
        storage_type=row_stock["storage_type"] if row_stock else None,
        size_group=row_stock["size_group"] if row_stock else None,
        stock_parse_error=stock_parse_error
    )
    
    # D) Revenue daily chart
    query_chart = """
        SELECT 
          day::text AS day, 
          COALESCE(sum(revenue_sum), 0) AS revenue_sum
        FROM app.v_sales_daily
        WHERE user_id = %(user_id)s
          AND shop_id = %(shop_id)s::uuid
          AND barcode = %(barcode)s
          AND day BETWEEN %(date_from)s AND %(date_to)s
        GROUP BY day
        ORDER BY day
    """
    
    rows_chart = execute_all(query_chart, params)
    
    revenue_daily = [
        {"day": row["day"], "revenue_sum": float(row["revenue_sum"])}
        for row in rows_chart
    ]
    
    return ProductDetailResponse(
        period=PeriodInfo(
            code=code,
            date_from=date_from.isoformat(),
            date_to=date_to.isoformat()
        ),
        filters=Filters(shop_id=shop_id_normalized, q=barcode),
        product=product_info,
        sales=product_sales,
        finance=product_finance,
        stock=product_stock,
        charts={"revenue_daily": revenue_daily}
    )
