from typing import Optional
from pydantic import BaseModel
from .common import PeriodInfo, Filters


# Revenue charts
class RevenuePoint(BaseModel):
    date: str  # YYYY-MM-DD format
    value: float


class RevenueFilters(BaseModel):
    shop_id: Optional[str] = None


class RevenueDailyResponse(BaseModel):
    points: list[RevenuePoint]
    period: PeriodInfo
    filters: RevenueFilters


# Stock charts
class StockItem(BaseModel):
    barcode: str
    sku: str
    product_name: Optional[str] = None
    stock_qty: Optional[float] = None
    coverage_days: Optional[float] = None
    turnover_days: Optional[float] = None
    fee_total_30d: Optional[float] = None
    storage_type: Optional[str] = None
    size_group: Optional[str] = None


class StockFilters(BaseModel):
    shop_id: Optional[str] = None
    q: Optional[str] = None


class StockCurrentResponse(BaseModel):
    items: list[StockItem]
    filters: StockFilters


# Legacy/other charts (keep for backward compatibility)
class ChartPoint(BaseModel):
    date: str
    value: float


class ChartRevenueDailyResponse(BaseModel):
    period: PeriodInfo
    filters: Filters
    points: list[ChartPoint]


class ChartStockCurrentResponse(BaseModel):
    filters: Filters
    items: list[StockItem]
