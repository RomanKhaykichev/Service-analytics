from typing import Optional
from pydantic import BaseModel
from .common import PeriodInfo, Filters, Paging


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
    items: list[ProductItem]
