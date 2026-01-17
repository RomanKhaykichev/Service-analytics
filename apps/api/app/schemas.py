from typing import Optional, List
from pydantic import BaseModel


# Common
class PeriodInfo(BaseModel):
    code: str
    date_from: str
    date_to: str


class Filters(BaseModel):
    shop_id: Optional[str] = None
    q: Optional[str] = None


# Shops
class Shop(BaseModel):
    shop_id: str
    shop_name: str


class ShopsResponse(BaseModel):
    shops: List[Shop]


# Charts
class ChartPoint(BaseModel):
    date: str
    value: float


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
