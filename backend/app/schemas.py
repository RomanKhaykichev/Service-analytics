from typing import Optional, List
from pydantic import BaseModel


# Common
class PeriodInfo(BaseModel):
    code: str
    date_from: str
    date_to: str


class Filters(BaseModel):
    shop_id: Optional[str] = None


# Shops
class Shop(BaseModel):
    shop_id: str
    shop_name: str


class ShopsResponse(BaseModel):
    shops: List[Shop]


# KPI Global
class KPIGlobalResponse(BaseModel):
    revenue_ytd: float


# KPI Filtered
class SalesMetrics(BaseModel):
    orders_cnt: int
    qty: int
    returns_qty: int
    buyouts_qty: int
    buyout_ratio: Optional[float] = None
    avg_check: Optional[float] = None


class FinanceMetrics(BaseModel):
    revenue_sum: float
    expenses_sum: float
    profit_sum: float
    margin_ratio: Optional[float] = None


class KPIFilteredResponse(BaseModel):
    period: PeriodInfo
    filters: Filters
    sales: SalesMetrics
    finance: FinanceMetrics


# Charts
class ChartPoint(BaseModel):
    day: str
    revenue_sum: float


class ChartRevenueDailyResponse(BaseModel):
    period: PeriodInfo
    filters: Filters
    points: List[ChartPoint]


class StockItem(BaseModel):
    barcode: str
    sku: str
    product_name: Optional[str] = None
    stock_qty: Optional[float] = None
    coverage_days: Optional[float] = None
    turnover_days: Optional[float] = None


class ChartStockCurrentResponse(BaseModel):
    filters: Filters
    items: List[StockItem]


# Products List
class Paging(BaseModel):
    limit: int
    offset: int
    total: int


class ProductItem(BaseModel):
    barcode: str
    sku: str
    product_name: Optional[str] = None
    category: Optional[str] = None
    orders_cnt: int
    qty: int
    returns_qty: int
    revenue_sum: float
    profit_sum: float
    margin_ratio: Optional[float] = None
    stock_qty: Optional[float] = None
    coverage_days: Optional[float] = None
    turnover_days: Optional[float] = None


class ProductsResponse(BaseModel):
    period: PeriodInfo
    filters: Filters
    paging: Paging
    items: List[ProductItem]


# Product Detail
class ProductInfo(BaseModel):
    barcode: str
    sku: str
    name: Optional[str] = None
    category: Optional[str] = None


class ProductSales(BaseModel):
    orders_cnt: int
    qty: int
    returns_qty: int
    buyouts_qty: int
    buyout_ratio: Optional[float] = None
    revenue_sum: float
    avg_check: Optional[float] = None


class ProductFinance(BaseModel):
    commission_sum: float
    logistics_sum: float
    promo_sum: float
    cogs_sum: float
    expenses_sum: float
    profit_sum: float
    margin_ratio: Optional[float] = None


class ProductStock(BaseModel):
    stock_qty: Optional[float] = None
    coverage_days: Optional[float] = None
    turnover_days: Optional[float] = None
    fee_total_30d: Optional[float] = None
    storage_type: Optional[str] = None
    size_group: Optional[str] = None
    stock_parse_error: bool = False


class ProductDetailResponse(BaseModel):
    period: PeriodInfo
    filters: Filters
    product: ProductInfo
    sales: ProductSales
    finance: ProductFinance
    stock: ProductStock
    charts: dict  # {"revenue_daily": [{"day": "...", "revenue_sum": ...}]}
