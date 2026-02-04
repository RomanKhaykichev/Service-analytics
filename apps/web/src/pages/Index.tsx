import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { ShoppingCart, Truck, Package, RotateCcw, Percent, CreditCard, DollarSign, TrendingDown, Wallet, Target, BarChart3, TrendingUp, ArrowDown, AlertTriangle, Boxes, Warehouse, Tag, ShoppingBag, Receipt, Info } from "lucide-react";
import { MainLayout } from "@/components/layout/MainLayout";
import { SummaryTabs } from "@/components/dashboard/SummaryTabs";
import { SummaryFilters } from "@/components/dashboard/SummaryFilters";
import { SummaryBlock } from "@/components/dashboard/SummaryBlock";
import { RevenueProgressBar } from "@/components/dashboard/RevenueProgressBar";
import { RevenueDailyChart } from "@/components/dashboard/RevenueDailyChart";
import { UzumServicesChart } from "@/components/dashboard/UzumServicesChart";
import { MonthlyTable } from "@/components/dashboard/MonthlyTable";
import { DailyView } from "@/components/dashboard/DailyView";
import { ExpensesView } from "@/components/dashboard/ExpensesView";
import { ShipmentView } from "@/components/dashboard/ShipmentView";
import { HeaderActions } from "@/components/dashboard/HeaderActions";
import { ProductsView } from "@/components/dashboard/ProductsView";
import { useDashboardMetrics } from "@/hooks/useDashboardMetrics";
import { useCumulativeRevenueGlobal } from "@/hooks/useCumulativeRevenueGlobal";
import { useStorageShops } from "@/hooks/useStorageShops";
import { useRevenueDaily } from "@/hooks/useRevenueDaily";
import { useStockCurrent } from "@/hooks/useStockCurrent";
import { useUzumServicesDaily } from "@/hooks/useUzumServicesDaily";
import { formatCurrency, formatQuantity, formatPercent, formatTrend, formatMoneyNoDecimals } from "@/lib/formatters";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { DateRangeProvider, useDateRange } from "@/contexts/DateRangeContext";

function Dashboard() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState("summary");
  const [store, setStore] = useState(() => searchParams.get("shop") ?? "all");
  const [viewMode, setViewMode] = useState("day");

  const {
    dateFrom,
    dateTo,
    setDateRange,
    minDate,
    maxDate,
    boundsLoading,
    defaultDateFrom,
    defaultDateTo,
  } = useDateRange();

  // Фильтр магазинов: используем ТОЛЬКО магазины из seller-storage (колонка "Магазин")
  const { shops } = useStorageShops();
  
  // Для seller-storage фильтрация по строке магазина (shop), а не по UUID (shop_id)
  const selectedShop = store === "all" ? undefined : store;  // строка магазина из seller-storage
  const { metrics, loading, error } = useDashboardMetrics(dateFrom, dateTo, undefined, selectedShop);
  const { cumulativeRevenue: cumulativeRevenueGlobal } = useCumulativeRevenueGlobal();
  const shopId = null;  // Не используем shop_id для seller-storage метрик

  // Load revenue and UZUM services data (filtered by selectedShop via barcode_norm)
  const { points: revenuePoints } = useRevenueDaily({ dateFrom, dateTo, shopId, shop: selectedShop });
  const { items: stockItems } = useStockCurrent({ limit: 50, shopId, shop: selectedShop });
  const { points: uzumServicesPoints, loading: uzumServicesLoading, error: uzumServicesError } = useUzumServicesDaily({ dateFrom, dateTo, shopId, shop: selectedShop });

  // Transform revenue data for RevenueDailyChart (YYYY-MM-DD -> dd.MM)
  const revenueChartData = revenuePoints.length > 0 ? revenuePoints.map((point) => {
    const [year, month, day] = point.date.split("-");
    return {
      date: `${day}.${month}`,
      revenue: point.revenue ?? 0,
      orders: point.orders ?? 0,
      avgCheck: point.averageCheck ?? 0,
    };
  }) : undefined;

  useEffect(() => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (store !== "all") next.set("shop", store);
      else next.delete("shop");
      return next;
    });
  }, [store]);

  // Loading skeleton for metrics
  const LoadingBlock = () => (
    <div className="space-y-2">
      {[...Array(6)].map((_, i) => (
        <Skeleton key={i} className="h-8 w-full" />
      ))}
    </div>
  );

  const salesMetrics = metrics ? [
    {
      icon: <ShoppingCart className="w-4 h-4" />,
      label: "Заказы",
      value: formatQuantity(metrics.ordersCount),
      subValue: formatCurrency(metrics.ordersValue),
      tooltip: "Общее количество заказов и их сумма"
    },
    {
      icon: <Truck className="w-4 h-4" />,
      label: "В обработке",
      value: formatQuantity(metrics.processingCount),
      subValue: formatCurrency(metrics.processingValue),
      tooltip: "Заказы в процессе обработки"
    },
    {
      icon: <Package className="w-4 h-4" />,
      label: "Выкупы",
      value: formatQuantity(metrics.completedCount),
      subValue: formatCurrency(metrics.completedValue),
      tooltip: "Успешно выкупленные заказы"
    },
    {
      icon: <RotateCcw className="w-4 h-4" />,
      label: "Возвраты",
      value: formatQuantity(metrics.returnsCount),
      subValue: metrics.returnsValue > 0 ? `-${formatCurrency(metrics.returnsValue)}` : formatCurrency(0),
      tooltip: "Возвращённые товары"
    },
    {
      icon: <Percent className="w-4 h-4" />,
      label: "Процент возврата заказов",
      value: formatPercent(metrics?.returnRate),
      tooltip: "Доля возвращённых заказов от общего числа"
    },
    {
      icon: <CreditCard className="w-4 h-4" />,
      label: "Средний чек",
      value: formatMoneyNoDecimals(metrics.averageCheck),
      tooltip: "Средняя сумма одного заказа"
    }
  ] : [];

  const financeMetrics = metrics ? [
    {
      icon: <DollarSign className="w-4 h-4" />,
      label: "Выручка",
      value: formatCurrency(metrics.revenue),
      tooltip: "Выручка со статусом «завершен»"
    },
    {
      icon: <TrendingDown className="w-4 h-4" />,
      label: "Расходы",
      value: formatCurrency(metrics.totalExpenses),
      tooltip: "Сумма всех расходов из блока Расходы."
    },
    {
      icon: <Wallet className="w-4 h-4" />,
      label: "Прибыль",
      value: formatCurrency(metrics.profit),
      tooltip: "Выручка минус Расходы"
    },
    {
      icon: <Target className="w-4 h-4" />,
      label: "Рентабельность продаж",
      value: formatPercent(metrics?.salesProfitability),
      tooltip: "Выручка / Себестоимость (завершённые заказы)"
    },
    {
      icon: <BarChart3 className="w-4 h-4" />,
      label: "Окупаемость инвестиций",
      value: formatPercent(metrics?.roi),
      tooltip: "ROI = (Выручка - Себестоимость) / Себестоимость × 100%"
    },
    {
      icon: <TrendingUp className="w-4 h-4" />,
      label: "Тренд выручки",
      value: formatTrend(metrics.revenueTrend),
      trend: (metrics.revenueTrend ?? 0) >= 0 ? "up" as const : "down" as const,
      trendValue: "",
      tooltip: "Сравнение выручки с аналогичным предыдущим периодом"
    },
    {
      icon: <ArrowDown className="w-4 h-4" />,
      label: "Упущенная выручка",
      value: formatCurrency(metrics.lostRevenue),
      tooltip: "Потенциальная выручка от товаров без остатков (avg продаж × цена × 15 дней)"
    }
  ] : [];

  // Основные метрики расходов (зависят от выбранного магазина)
  const expenseMetrics = metrics ? [
    {
      icon: <Percent className="w-4 h-4" />,
      label: "Комиссия UZUM",
      value: formatCurrency(metrics.uzumCommission),
      tooltip: "Комиссия маркетплейса из отчёта о продажах"
    },
    {
      icon: <Truck className="w-4 h-4" />,
      label: "Логистика UZUM",
      value: formatCurrency(metrics.uzumLogistics),
      tooltip: "Логистический сбор из отчёта о продажах"
    },
    {
      icon: <Boxes className="w-4 h-4" />,
      label: "Себест. прод. тов.",
      value: formatCurrency(metrics.productCost),
      tooltip: "Себестоимость × количество (в обработке + завершен)"
    },
    {
      icon: <Receipt className="w-4 h-4" />,
      label: "Налоги 1%",
      value: formatCurrency(metrics.taxes1pct),
      tooltip: "Налоги 1% от выручки (завершённые заказы)"
    },
    {
      icon: <Info className="w-4 h-4" />,
      label: "Доп. расходы",
      value: formatCurrency(metrics.extraExpenses),
      tooltip: "Расходы занесенные во вкладке Доп. расходы."
    }
  ] : [];

  // Метрики услуг UZUM (не зависят от выбранного магазина)
  // Порядок: Хранение, Реклама, Штрафы (как на скриншоте)
  const uzumServicesMetrics = metrics ? [
    {
      icon: <Warehouse className="w-4 h-4" />,
      label: "Хранение UZUM",
      value: formatCurrency(metrics.uzumStorage),
      tooltip: "Оплата за услуги хранения"
    },
    {
      icon: <Target className="w-4 h-4" />,
      label: "Реклама UZUM",
      value: formatCurrency(metrics.uzumAds),
      tooltip: "Расходы на маркетинг (источник = маркетинг, тип = оплата)"
    },
    {
      icon: <AlertTriangle className="w-4 h-4" />,
      label: "Штрафы UZUM",
      value: formatCurrency(metrics.uzumFines),
      tooltip: "Штрафы (услуга содержит слово ШТРАФ)"
    }
  ] : [];

  const stockQty = metrics?.stockQuantity ?? 0;
  const stockCost = metrics?.stockCost ?? 0;
  const stockRetail = metrics?.stockRetailPrice ?? 0;
  const stockHasData = metrics?.stockHasData ?? false;
  const stockIsZero = metrics?.stockIsZero ?? false;
  const stockZeroReason = metrics?.stockZeroReason ?? null;
  const stockSource = metrics?.stockSource ?? null;
  const stockSkuTotal = metrics?.stockSkuTotal ?? 0;
  const stockSkuWithStock = metrics?.stockSkuWithStock ?? 0;
  const stockSnapshotAt = metrics?.stockSnapshotAt ?? null;
  // Предупреждение "Склад = 0" только при источнике leftout_old и явном нуле (не "нет данных")
  const showStockZeroWarning = stockSource === 'leftout_old' && stockIsZero;

  const warehouseMetrics = metrics ? [
    {
      icon: <Warehouse className="w-4 h-4" />,
      label: "Товаров на складе",
      value: formatQuantity(stockQty),
      tooltip: "SUM(В продаже) из left-out-report_old"
    },
    {
      icon: <Tag className="w-4 h-4" />,
      label: "Себест. тов.",
      value: formatCurrency(stockCost),
      tooltip: "SUM(В продаже × Себест. (сумы)) из left-out-report_old"
    },
    {
      icon: <ShoppingBag className="w-4 h-4" />,
      label: "Рознич. цена",
      value: formatCurrency(stockRetail),
      tooltip: "SUM(В продаже × Стоимость продажи (сумы)) из left-out-report_old"
    }
  ] : [];

  return (
    <MainLayout>
      {/* Header with title and actions */}
      <div className="flex flex-col gap-4 mb-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold text-foreground">Мои продажи на</h1>
            <span className="px-3 py-1.5 bg-primary/10 text-primary font-semibold rounded-lg">UZUM</span>
          </div>
          
          {/* Center - Compact Revenue Progress Bar (all tabs) */}
          <div className="hidden lg:flex flex-1 justify-center">
            <RevenueProgressBar 
              current={cumulativeRevenueGlobal} 
              target={1000000000} 
              compact 
            />
          </div>
          
          <div className="flex items-center gap-2">
            <HeaderActions />
          </div>
        </div>
        
        {/* Mobile Revenue Progress Bar (all tabs) */}
        <div className="lg:hidden">
          <RevenueProgressBar 
            current={cumulativeRevenueGlobal} 
            target={1000000000} 
            compact 
          />
        </div>

        {/* Filters: скрыты на Доп. расходы и По месячно; на Отгрузка — только магазин (без периода) */}
        <div className="flex items-center justify-end gap-4 min-h-10">
          {activeTab === "expenses" || activeTab === "monthly" ? (
            <div className="min-h-10" aria-hidden />
          ) : (
            <SummaryFilters 
              dateFrom={dateFrom}
              dateTo={dateTo}
              onDateRangeChange={setDateRange}
              store={store}
              onStoreChange={setStore}
              viewMode={viewMode}
              onViewModeChange={setViewMode}
              showStoreFilter={activeTab !== "daily"}
              showViewMode={activeTab === "daily"}
              showPeriodFilter={activeTab !== "shipment"}
              shops={shops}
              minDate={minDate ?? undefined}
              maxDate={maxDate ?? undefined}
              boundsLoading={boundsLoading}
              defaultDateFrom={defaultDateFrom ?? undefined}
              defaultDateTo={defaultDateTo ?? undefined}
            />
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center justify-between gap-4">
        <SummaryTabs activeTab={activeTab} onTabChange={setActiveTab} />
      </div>

      {/* Content based on active tab */}
      {activeTab === "monthly" ? (
        <div className="mt-6">
          <MonthlyTable
            year={maxDate ? new Date(maxDate).getFullYear() : new Date().getFullYear()}
            shop={null}
          />
        </div>
      ) : activeTab === "daily" ? (
        <div className="mt-6">
          <DailyView viewMode={viewMode} dateFrom={dateFrom} dateTo={dateTo} shopId={null} shop={null} />
        </div>
      ) : activeTab === "products" ? (
        <div className="mt-6">
          <ProductsView />
        </div>
      ) : activeTab === "expenses" ? (
        <div className="mt-6">
          <ExpensesView />
        </div>
      ) : activeTab === "shipment" ? (
        <div className="mt-6">
          <ShipmentView />
        </div>
      ) : (
        <>
          {/* 4 KPI Blocks */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mt-6 items-stretch">
            {loading ? (
              <>
                <div className="bg-card rounded-xl border border-border p-4"><LoadingBlock /></div>
                <div className="bg-card rounded-xl border border-border p-4"><LoadingBlock /></div>
                <div className="bg-card rounded-xl border border-border p-4"><LoadingBlock /></div>
                <div className="bg-card rounded-xl border border-border p-4"><LoadingBlock /></div>
              </>
            ) : error ? (
              <div className="col-span-4 text-center text-destructive py-8">
                Ошибка загрузки данных: {error}
              </div>
            ) : (
              <>
                <SummaryBlock title="ПРОДАЖИ" titleColor="text-chart-4" metrics={salesMetrics} />
                <SummaryBlock title="ФИНАНСЫ" titleColor="text-warning" metrics={financeMetrics} />
                <SummaryBlock 
                  title="РАСХОДЫ" 
                  titleColor="text-destructive" 
                  metrics={expenseMetrics} 
                />
                <div className="flex flex-col h-full gap-4">
                  <SummaryBlock 
                    title="СКЛАД" 
                    titleColor="text-warning" 
                    metrics={warehouseMetrics} 
                    customHeightClass="h-auto"
                    customOverflowClass="overflow-visible"
                    customPadding="px-4 pb-4"
                    customSpacing="space-y-1"
                    emptyState={
                      !loading && showStockZeroWarning ? (
                        <Alert variant="destructive" className="m-0">
                          <AlertTriangle className="h-4 w-4" />
                          <AlertTitle>Склад = 0</AlertTitle>
                          <AlertDescription>
                            <p className="mb-2">
                              {stockZeroReason === "all_zero_in_snapshot"
                                ? "По последней выгрузке склада (left-out-report_old) сумма «В продаже» = 0. Проверь файл склада/остатков."
                                : "По данным left-out-report_old на складе 0. Проверь выгрузку «Склад» или фильтр магазина."}
                            </p>
                            {(stockSkuTotal > 0 || stockSkuWithStock >= 0 || stockSnapshotAt) && (
                              <div className="text-xs text-muted-foreground space-y-1">
                                {stockSkuTotal > 0 && (
                                  <p>SKU: {stockSkuTotal}, с остатком: {stockSkuWithStock}</p>
                                )}
                                {stockSnapshotAt && (
                                  <p>Срез: {new Date(stockSnapshotAt).toLocaleString("ru-RU")}</p>
                                )}
                              </div>
                            )}
                          </AlertDescription>
                        </Alert>
                      ) : !loading && !stockHasData && stockSource === null ? (
                        <p className="text-sm text-muted-foreground m-0">Нет данных по складу. Загрузите файл left-out-report_old.</p>
                      ) : undefined
                    }
                  />
                  <SummaryBlock 
                    title="УСЛУГИ UZUM" 
                    titleColor="text-primary" 
                    metrics={uzumServicesMetrics} 
                    customBorderClass="border-violet-400 dark:border-violet-500"
                    customMinHeight="min-h-[180px]"
                    customPadding="px-4 pb-3"
                    customSpacing="space-y-1.5"
                  />
                </div>
              </>
            )}
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
            <RevenueDailyChart data={revenueChartData} />
            <UzumServicesChart points={uzumServicesPoints} loading={uzumServicesLoading} error={uzumServicesError} />
          </div>
        </>
      )}
    </MainLayout>
  );
}

const Index = () => (
  <DateRangeProvider>
    <Dashboard />
  </DateRangeProvider>
);

export default Index;
