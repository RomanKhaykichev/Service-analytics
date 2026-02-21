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
import { useSalesDateRange } from "@/hooks/useSalesDateRange";
import { formatCurrency, formatQuantity, formatPercent, formatTrend, formatMoneyNoDecimals } from "@/lib/formatters";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { DateRangeProvider, useDateRange } from "@/contexts/DateRangeContext";

function Dashboard() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState("summary");
  const [store, setStore] = useState(() => searchParams.get("shop") ?? "all");
  const [viewMode, setViewMode] = useState("day");
  // Состояние вкладки «Отгрузка»: кнопка «Рассчитать» пересчитывает всю таблицу (все товары без фильтра); данные общие для всех магазинов до следующего пересчёта
  const [shipmentDaysUntilShipment, setShipmentDaysUntilShipment] = useState(7);
  const [shipmentConsiderStock, setShipmentConsiderStock] = useState<string>("yes");
  const [shipmentCalculatedByKey, setShipmentCalculatedByKey] = useState<Record<string, number>>({});
  const setShipmentCalculatedRecommended = (map: Record<string, number>) => {
    setShipmentCalculatedByKey(map);
  };

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
  const { cumulativeRevenue: cumulativeRevenueGlobal, cumulativeRevenueYear } = useCumulativeRevenueGlobal();
  const shopId = null;  // Не используем shop_id для seller-storage метрик
  
  // Диапазон дат из fact_sales (sells_report "Дата создания")
  const { minDate: salesMinDate, maxDate: salesMaxDate } = useSalesDateRange();

  // Пользовательский процент для налога (по умолчанию 1%)
  const [taxPercentInput, setTaxPercentInput] = useState("1");
  const [taxPercent, setTaxPercent] = useState(1);

  const handleTaxPercentKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      const parsed = parseFloat(taxPercentInput.replace(",", "."));
      if (!isNaN(parsed) && parsed >= 0 && parsed <= 100) {
        setTaxPercent(parsed);
      }
    }
  };

  // Пересчёт метрик, зависящих от налога, на фронте
  const revenueValue = metrics?.revenue ?? 0;
  const commissionValue = metrics?.uzumCommission ?? 0;
  const logisticsValue = metrics?.uzumLogistics ?? 0;
  const productCostValue = metrics?.productCost ?? 0;
  const extraExpensesValue = metrics?.extraExpenses ?? 0;

  // Налог = Выручка × указанный процент
  const adjustedTax = revenueValue * (taxPercent / 100);

  // Расходы = Комиссия UZUM + Логистика UZUM + Себест. прод. тов. + Налог + Доп. расходы
  const adjustedTotalExpenses =
    commissionValue +
    logisticsValue +
    productCostValue +
    adjustedTax +
    extraExpensesValue;

  // Прибыль = Выручка – Расходы
  const adjustedProfit = revenueValue - adjustedTotalExpenses;

  // Рентабельность и ROI пересчитываем из новых прибыли/расходов
  const adjustedSalesProfitability = revenueValue > 0 ? (adjustedProfit / revenueValue) * 100 : 0;
  const adjustedRoi = adjustedTotalExpenses > 0 ? (adjustedProfit / adjustedTotalExpenses) * 100 : 0;

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
      profit: point.profit ?? 0,
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
      tooltip: "Общее кол-во заказов за выбранный период."
    },
    {
      icon: <Truck className="w-4 h-4" />,
      label: "В обработке",
      value: formatQuantity(metrics.processingCount),
      subValue: formatCurrency(metrics.processingValue),
      tooltip: "Заказы по которым ожидается оплата."
    },
    {
      icon: <Package className="w-4 h-4" />,
      label: "Выкупы",
      value: formatQuantity(metrics.completedCount),
      subValue: formatCurrency(metrics.completedValue),
      tooltip: "Заказы которые клиент забрал, и прошло 10 дней."
    },
    {
      icon: <RotateCcw className="w-4 h-4" />,
      label: "Возвраты",
      value: formatQuantity(metrics.returnsCount),
      subValue: metrics.returnsValue > 0 ? `-${formatCurrency(metrics.returnsValue)}` : formatCurrency(0),
      tooltip: "Заказы которые клиент вернул или отменил."
    },
    {
      icon: <Percent className="w-4 h-4" />,
      label: "Процент возврата заказов",
      value: formatPercent(metrics?.returnRate),
      tooltip: "Отношение отменённых заказов к выкупленным заказам, выраженное в процентах."
    },
    {
      icon: <CreditCard className="w-4 h-4" />,
      label: "Средний чек",
      value: formatMoneyNoDecimals(metrics.averageCheck),
      tooltip: "Средняя стоимость заказа за период."
    }
  ] : [];

  const financeMetrics = metrics ? [
    {
      icon: <DollarSign className="w-4 h-4" />,
      label: "Выручка",
      value: formatCurrency(metrics.revenue),
      tooltip: "Общая сумма денег, полученная вами от реализации товаров."
    },
    {
      icon: <TrendingDown className="w-4 h-4" />,
      label: "Расходы",
      value: formatCurrency(adjustedTotalExpenses),
      tooltip: "Сумма всех расходов, представленных во вкладке «Расходы» (услуги UZUM не учитываются)."
    },
    {
      icon: <Wallet className="w-4 h-4" />,
      label: "Прибыль",
      value: formatCurrency(adjustedProfit),
      tooltip: "Выручка – Расходы."
    },
    {
      icon: <Target className="w-4 h-4" />,
      label: "Рентабельность продаж",
      value: formatPercent(adjustedSalesProfitability),
      tooltip: "(Прибыль / Выручка) × 100. Показывает, какая часть выручки является прибылью."
    },
    {
      icon: <BarChart3 className="w-4 h-4" />,
      label: "Окупаемость инвестиций",
      value: formatPercent(adjustedRoi),
      tooltip: "(Прибыль / себестоимость товаров) × 100. Показывает, насколько выгодно вложение денег."
    },
    {
      icon: <TrendingUp className="w-4 h-4" />,
      label: "Тренд выручки",
      value: formatTrend(metrics.revenueTrend),
      trend: (metrics.revenueTrend ?? 0) >= 0 ? "up" as const : "down" as const,
      trendValue: "",
      tooltip: "Сравнение выручки за выбранный текущий период с выручкой за аналогичный период ранее."
    },
    {
      icon: <ArrowDown className="w-4 h-4" />,
      label: "Упущенная выручка",
      value: formatCurrency(metrics.lostRevenue),
      tooltip: "Потенциальная потеря выручки за период из-за отсутствия товаров на складе = (кол-во дней без товара) × (средняя выручка за день) для всех товаров."
    }
  ] : [];

  // Основные метрики расходов (зависят от выбранного магазина)
  const expenseMetrics = metrics ? [
    {
      icon: <Percent className="w-4 h-4" />,
      label: "Комиссия UZUM",
      value: formatCurrency(metrics.uzumCommission),
      tooltip: ""
    },
    {
      icon: <Truck className="w-4 h-4" />,
      label: "Логистика UZUM",
      value: formatCurrency(metrics.uzumLogistics),
      tooltip: ""
    },
    {
      icon: <Boxes className="w-4 h-4" />,
      label: "Себест. прод. тов.",
      value: formatCurrency(metrics.productCost),
      tooltip: ""
    },
    {
      icon: <Receipt className="w-4 h-4" />,
      label: (
        <div className="flex items-center gap-1">
          <span>Налоги</span>
          <input
            type="number"
            value={taxPercentInput}
            onChange={(e) => setTaxPercentInput(e.target.value)}
            onKeyDown={handleTaxPercentKeyDown}
            className="w-12 h-6 text-xs px-1 border border-border rounded bg-background text-foreground"
            min={0}
            max={100}
          />
          <span>%</span>
        </div>
      ),
      value: formatCurrency((metrics.revenue ?? 0) * (taxPercent / 100)),
      tooltip: ""
    },
    {
      icon: <Info className="w-4 h-4" />,
      label: "Доп. расходы",
      value: formatCurrency(metrics.extraExpenses),
      tooltip: "Расходы, указанные вами во вкладке «Доп. расходы»."
    }
  ] : [];

  // Метрики услуг UZUM (не зависят от выбранного магазина)
  // Порядок: Хранение, Реклама, Штрафы (как на скриншоте)
  const uzumServicesMetrics = metrics ? [
    {
      icon: <Warehouse className="w-4 h-4" />,
      label: "Хранение UZUM",
      value: formatCurrency(metrics.uzumStorage),
      tooltip: "Стоимость платного хранения товаров за выбранный период."
    },
    {
      icon: <Target className="w-4 h-4" />,
      label: "Реклама UZUM",
      value: formatCurrency(metrics.uzumAds),
      tooltip: "Стоимость маркетинговых кампаний (БУСТ в топ) за выбранный период."
    },
    {
      icon: <AlertTriangle className="w-4 h-4" />,
      label: "Штрафы UZUM",
      value: formatCurrency(metrics.uzumFines),
      tooltip: "Начисленные штрафы за выбранный период."
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
      tooltip: "Кол-во товаров, хранящихся на складе UZUM для продажи по FBO."
    },
    {
      icon: <Tag className="w-4 h-4" />,
      label: "Себест. тов.",
      value: formatCurrency(stockCost),
      tooltip: ""
    },
    {
      icon: <ShoppingBag className="w-4 h-4" />,
      label: "Рознич. цена",
      value: formatCurrency(stockRetail),
      tooltip: "Стоимость товаров, хранящихся на складе UZUM, при продаже их по ценам маркетплейса."
    }
  ] : [];

  return (
    <MainLayout>
      {/* Header with title and actions */}
      <div className="flex flex-col gap-4 mb-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-semibold text-foreground">Мои продажи на</h1>
              <span className="px-3 py-1.5 bg-primary/10 text-primary font-semibold rounded-lg">UZUM</span>
            </div>
            {salesMinDate && salesMaxDate && (() => {
              const formatDate = (dateStr: string) => {
                const date = new Date(dateStr);
                const day = String(date.getDate()).padStart(2, "0");
                const month = String(date.getMonth() + 1).padStart(2, "0");
                const year = date.getFullYear();
                return `${day}.${month}.${year}`;
              };
              return (
                <div className="text-xs text-muted-foreground/80 pl-1">
                  от <span className="font-medium">{formatDate(salesMinDate)}</span> до <span className="font-medium">{formatDate(salesMaxDate)}</span>
                </div>
              );
            })()}
          </div>
          
          {/* Center - Compact Revenue Progress Bar (all tabs) */}
          <div className="hidden lg:flex flex-1 justify-center">
            <RevenueProgressBar 
              current={cumulativeRevenueGlobal} 
              target={1000000000} 
              year={cumulativeRevenueYear}
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
            year={cumulativeRevenueYear}
            compact 
          />
        </div>
      </div>

      {/* Tabs и фильтры на одном уровне */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mt-24">
        <SummaryTabs activeTab={activeTab} onTabChange={setActiveTab} />
        {activeTab !== "expenses" && activeTab !== "monthly" ? (
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
        ) : (
          <div className="min-h-10" aria-hidden />
        )}
      </div>

      {/* Content based on active tab */}
      {activeTab === "monthly" ? (
        <div className="mt-6">
          <MonthlyTable
            year={maxDate ? new Date(maxDate).getFullYear() : new Date().getFullYear()}
            shop={null}
            taxPercent={taxPercent}
          />
        </div>
      ) : activeTab === "daily" ? (
        <div className="mt-6">
          <DailyView
            viewMode={viewMode}
            dateFrom={dateFrom}
            dateTo={dateTo}
            shopId={null}
            shop={null}
            taxPercent={taxPercent}
          />
        </div>
      ) : activeTab === "products" ? (
        <div className="mt-6">
          <ProductsView shop={selectedShop} taxPercent={taxPercent} dateFrom={dateFrom} dateTo={dateTo} />
        </div>
      ) : activeTab === "expenses" ? (
        <div className="mt-6">
          <ExpensesView />
        </div>
      ) : activeTab === "shipment" ? (
        <div className="mt-6">
          <ShipmentView
            shop={store === "all" ? undefined : store}
            daysUntilShipment={shipmentDaysUntilShipment}
            setDaysUntilShipment={setShipmentDaysUntilShipment}
            considerStock={shipmentConsiderStock}
            setConsiderStock={setShipmentConsiderStock}
            calculatedRecommendedByKey={shipmentCalculatedByKey}
            setCalculatedRecommended={setShipmentCalculatedRecommended}
          />
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
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6">
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
