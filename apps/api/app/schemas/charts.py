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
    shop: Optional[str] = None  # Seller-storage shop name (string) when filtering by barcode


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
    shop: Optional[str] = None  # Seller-storage shop name when filtering by barcode
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
    storage: float  # Хранение UZUM (fact_expenses)
    ads: float  # Реклама UZUM (fact_expenses)
    fines: float  # Штрафы UZUM (fact_expenses)
    commission: float = 0.0  # Комиссия UZUM (fact_sales, filterable by shop)
    logistics: float = 0.0  # Логистика UZUM (fact_sales, filterable by shop)


class UzumServicesFilters(BaseModel):
    shop_id: Optional[str] = None
    shop: Optional[str] = None  # Seller-storage shop name when filtering by barcode (applies to data that has barcode)


class UzumServicesDailyResponse(BaseModel):
    points: list[UzumServicesPoint]
    period: PeriodInfo
    filters: UzumServicesFilters


# Orders and Sales daily chart (all metrics)
class OrdersSalesDailyPoint(BaseModel):
    date: str  # YYYY-MM-DD format
    orders_qty: float  # Заказы
    buyouts_qty: float  # Выкупы
    returns_qty: float  # Возвраты
    stock_qty: float  # Складские остатки
    revenue_sum: float  # Выручка
    profit_sum: float  # Прибыль
    avg_check: float  # Средний чек


class OrdersSalesDailyFilters(BaseModel):
    shop_id: Optional[str] = None
    shop: Optional[str] = None  # Seller-storage shop name when filtering by barcode


class OrdersSalesDailyResponse(BaseModel):
    points: list[OrdersSalesDailyPoint]
    period: PeriodInfo
    filters: OrdersSalesDailyFilters


# Daily summary table (По дням — Данные по дням): same formulas as Сводка, GROUP BY day
class DailySummaryPoint(BaseModel):
    date: str  # YYYY-MM-DD
    orders: float  # Заказы = SUM(qty)
    buys: float  # Выкупы = SUM(qty) WHERE status completed
    returns: float  # Возвраты = SUM(returns_qty)
    revenue: float  # Выручка
    commission: float  # Комиссия
    logistics: float  # Логистика
    storage: float  # Хранение (MVP: 0 or daily fee)
    ads: float  # Реклама (manual_expenses category)
    penalties: float  # Штрафы (manual_expenses category)
    cogs: float  # Себест. прод. тов.
    taxes: float  # Налоги (manual_expenses category)
    profit: float  # Прибыль дневная


class DailySummaryFilters(BaseModel):
    shop_id: Optional[str] = None
    shop: Optional[str] = None  # Seller-storage shop name for barcode filter


class DailySummaryResponse(BaseModel):
    points: list[DailySummaryPoint]
    period: PeriodInfo
    filters: DailySummaryFilters


# Shipment recommendations (left-out-report_old, Оборачиваемость < 60)
class ShipmentRecommendationItem(BaseModel):
    product_name: Optional[str] = None  # Товар = Наименование
    sku: Optional[str] = None  # Артикул = SKU
    barcode: Optional[str] = None  # Штрихкод
    stock: Optional[str] = None  # На складе = Общий остаток
    sales_per_day: Optional[str] = None  # Продаж в день = Среднесуточные продажи
    recommended_qty: str = "-"  # Рекомендуемое кол-во
    to_ship: Optional[str] = None  # Запланировано к отгрузке = К отправке


class ShipmentRecommendationsResponse(BaseModel):
    items: list[ShipmentRecommendationItem]
