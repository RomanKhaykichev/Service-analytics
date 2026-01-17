# Export all schemas for backward compatibility
from . import auth
from .shops import Shop, ShopsResponse
from .common import PeriodInfo, Filters, Paging
from .charts import (
    RevenuePoint,
    RevenueFilters,
    RevenueDailyResponse,
    StockItem,
    StockFilters,
    StockCurrentResponse,
    ChartPoint,
    ChartRevenueDailyResponse,
    ChartStockCurrentResponse,
)
from .products import ProductItem, ProductsResponse

__all__ = [
    "auth",
    "Shop",
    "ShopsResponse",
    "PeriodInfo",
    "Filters",
    "Paging",
    "RevenuePoint",
    "RevenueFilters",
    "RevenueDailyResponse",
    "StockItem",
    "StockFilters",
    "StockCurrentResponse",
    "ChartPoint",
    "ChartRevenueDailyResponse",
    "ChartStockCurrentResponse",
    "ProductItem",
    "ProductsResponse",
]
