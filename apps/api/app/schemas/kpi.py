from pydantic import BaseModel


class CumulativeRevenueResponse(BaseModel):
    """Общая накопительная выручка пользователя за всё время, без фильтров по магазину и периоду."""
    cumulativeRevenue: float


class KPISummaryResponse(BaseModel):
    """KPI Summary response matching frontend DashboardMetrics interface."""
    cumulativeRevenue: float
    ordersCount: float
    ordersValue: float
    processingCount: float
    processingValue: float
    completedCount: float
    completedValue: float
    returnsCount: float
    returnsValue: float
    returnRate: float
    averageCheck: float
    revenue: float
    totalExpenses: float
    profit: float
    salesProfitability: float
    roi: float
    revenueTrend: float
    lostRevenue: float
    uzumCommission: float
    uzumLogistics: float
    uzumAds: float
    uzumStorage: float
    uzumFines: float
    taxes1pct: float
    productCost: float
    extraExpenses: float
    stockQuantity: float
    stockCost: float
    stockRetailPrice: float
