from typing import Optional
from pydantic import BaseModel
from .common import PeriodInfo, Filters


# Revenue charts
class RevenuePoint(BaseModel):
    date: str  # YYYY-MM-DD format
    revenue: float
    orders: float
    averageCheck: float


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


# Stock daily chart
class StockDailyPoint(BaseModel):
    date: str  # YYYY-MM-DD format
    orders: float
    stock: float


class StockDailyFilters(BaseModel):
    shop_id: Optional[str] = None


class StockDailyResponse(BaseModel):
    points: list[StockDailyPoint]
    period: PeriodInfo
    filters: StockDailyFilters


# UZUM Services daily chart
class UzumServicesPoint(BaseModel):
    date: str  # YYYY-MM-DD format
    storage: float  # Хранение UZUM
    ads: float  # Реклама UZUM
    fines: float  # Штрафы UZUM


class UzumServicesFilters(BaseModel):
    shop_id: Optional[str] = None  # Игнорируется для услуг (они общие)


class UzumServicesDailyResponse(BaseModel):
    points: list[UzumServicesPoint]
    period: PeriodInfo
    filters: UzumServicesFilters
