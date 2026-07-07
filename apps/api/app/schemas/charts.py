from typing import Optional
from pydantic import BaseModel
from .common import PeriodInfo, Filters


# Revenue charts
class RevenuePoint(BaseModel):
    date: str  # YYYY-MM-DD format
    revenue: float
    orders: float
    averageCheck: float
    # По дням на карточке товара (product_id): формулы из блоков Продажи и Финансы
    returns: Optional[float] = None  # SUM(returns_qty)
    profit: Optional[float] = None   # выручка − cogs − commission − logistics − 1% с выручки


class RevenueFilters(BaseModel):
    shop_id: Optional[str] = None
    shop: Optional[str] = None  # Seller-storage shop name (string) when filtering by barcode
    product_id: Optional[str] = None  # ID карточки товара — фильтр по штрихкодам из left-out


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
    recommended_qty: str = "-"  # Рекомендуемое кол-во (считается на фронте по кнопке Рассчитать)
    to_ship: Optional[str] = None  # Запланировано к отгрузке = К отправке
    turnover: Optional[float] = None  # Оборачиваемость (дней) из left-out-report_old для расчёта recommended_qty


class ShipmentRecommendationsResponse(BaseModel):
    items: list[ShipmentRecommendationItem]


# Products table (Товары): left-out-report_old + sells_report by barcode
class ProductsTableItem(BaseModel):
    product_id: Optional[str] = None     # ID товара (left-out-report_old), для группировки по карточкам
    product_name: Optional[str] = None   # Наименование (leftout_old)
    sku: Optional[str] = None           # Артикул = SKU (leftout_old)
    price: Optional[float] = None       # Цена = Стоимость продажи (сумы) (leftout_old)
    sales_qty: int = 0                  # Количество (sells_report, без фильтра по статусу)
    returns_qty: int = 0                # Возвраты (sells_report)
    orders_qty: int = 0                 # Заказы = В обработке + Выкупы + Возвраты (как на Сводке)
    orders_value: float = 0.0           # Сумма заказов (как на Сводке)
    processing_qty: int = 0             # В обработке (шт.)
    processing_value: float = 0.0       # В обработке (сум)
    completed_qty: int = 0              # Выкупы (шт.)
    completed_value: float = 0.0        # Выкупы (сум)
    returns_value: float = 0.0          # Возвраты (сум) = returns_qty × price_sum
    revenue: float = 0.0                # Выручка (сумы), статус «Завершен»
    profit: float = 0.0                 # Прибыль = Выручка - Себестоимость(заверш.) - Комиссия - Логистика - (Выручка*1%)
    turnover: Optional[float] = None   # Оборачиваемость (leftout_old)
    stock: Optional[int] = None         # Остаток = Общий остаток (leftout_old)
    fbs_stock: Optional[int] = None     # Остаток FBS (leftout_old)
    size_group: Optional[str] = None   # Габаритная группа; «Неопределенная» → «-»
    cogs: float = 0.0                   # Себестоимость (сумы) (sells_report) - удельная себестоимость для отображения
    cogs_total: float = 0.0             # Общая себестоимость = сумма (cogs_sum × (qty − returns_qty)) по завершённым продажам
    commission: float = 0.0             # Комиссия маркетплейса, статус «Завершен»
    logistics: float = 0.0             # Логистический сбор, статус «Завершен»
    abc_orders: Optional[str] = None   # ABC заказы (оставить как есть)
    abc_profit: Optional[str] = None   # ABC прибыль
    abc_revenue: Optional[str] = None  # ABC выручка
    barcode: Optional[str] = None     # Штрихкод (leftout_old)
    product_image_url: Optional[str] = None  # Превью товара (left-out-report, «Ссылка на товар»)
    rating: Optional[float] = None  # Рейтинг товара (Uzum API, product.rating)
    feedback_quantity: Optional[int] = None  # Количество отзывов (Uzum API, product.feedbackQuantity)
    storage_cost_per_day: Optional[float] = None  # Стоимость хранения 1 дня, сум
    shop: Optional[str] = None         # Магазин (sells_report)


class ProductsTableResponse(BaseModel):
    items: list[ProductsTableItem]


class ProductCardAllTimeMetrics(BaseModel):
    """Метрики карточки товара по всей выгрузке (без фильтра по датам): для Маржинальность и От общей выручки."""
    revenue: float = 0.0
    profit: float = 0.0
    total_revenue: float = 0.0


# Product comment schemas
class ProductCommentResponse(BaseModel):
    product_id: str
    comment: Optional[str] = None


class ProductCommentRequest(BaseModel):
    product_id: str
    comment: Optional[str] = None
