import { useState, useEffect, useCallback, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { ShoppingCart, Truck, Package, RotateCcw, Percent, CreditCard, DollarSign, TrendingDown, Wallet, Target, BarChart3, TrendingUp, ArrowDown, AlertTriangle, Boxes, Warehouse, Tag, ShoppingBag, Receipt, Info } from "lucide-react";
import { MainLayout } from "@/components/layout/MainLayout";
import { SummaryTabs } from "@/components/dashboard/SummaryTabs";
import { SummaryFilters } from "@/components/dashboard/SummaryFilters";
import { SummaryBlock } from "@/components/dashboard/SummaryBlock";
import { SummaryWeeklyInsights } from "@/components/dashboard/SummaryWeeklyInsights";
import { RevenueProgressBar } from "@/components/dashboard/RevenueProgressBar";
import { RevenueDailyChart } from "@/components/dashboard/RevenueDailyChart";
import { UzumServicesChart } from "@/components/dashboard/UzumServicesChart";
import { MonthlyTable } from "@/components/dashboard/MonthlyTable";
import { DailyView } from "@/components/dashboard/DailyView";
import { ExpensesView } from "@/components/dashboard/ExpensesView";
import { ShipmentView } from "@/components/dashboard/ShipmentView";
import { HeaderActions } from "@/components/dashboard/HeaderActions";
import type { UzumApiConnectDialogHandle } from "@/components/dashboard/UzumApiConnectDialog";
import { ProductsView, type ProductsTableItemType } from "@/components/dashboard/ProductsView";
import type { WeeklyInsightProduct } from "@/hooks/useSummaryWeeklyInsights";
import { useAuth } from "@/hooks/useAuth";
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
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { DateRangeProvider, useDateRange } from "@/contexts/DateRangeContext";
import { useLanguage } from "@/contexts/LanguageContext";
import { getWeeklyInsightRanges } from "@/lib/weekRanges";
import { getNextUzumSyncSchedule } from "@/lib/uzumSyncSchedule";

function Dashboard() {
  const { t, language } = useLanguage();
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState("summary");
  const [store, setStore] = useState(() => searchParams.get("shop") ?? "all");
  const [viewMode, setViewMode] = useState("day");
  // Состояние вкладки «Отгрузка»: кнопка «Рассчитать» пересчитывает всю таблицу (все товары без фильтра); данные общие для всех магазинов до следующего пересчёта
  const [shipmentDaysUntilShipment, setShipmentDaysUntilShipment] = useState(7);
  const [shipmentConsiderStock, setShipmentConsiderStock] = useState<string>("yes");
  const [shipmentCalculatedByKey, setShipmentCalculatedByKey] = useState<Record<string, number>>({});
  const [productToOpen, setProductToOpen] = useState<ProductsTableItemType | null>(null);
  const handleOpenProductHandled = useCallback(() => setProductToOpen(null), []);
  const apiConnectRef = useRef<UzumApiConnectDialogHandle>(null);
  const openApiConnect = useCallback(() => {
    apiConnectRef.current?.open();
  }, []);
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
  const { minDate: salesMinDate, maxDate: salesMaxDate, lastUpdatedAt } = useSalesDateRange();
  const [monthlyYear, setMonthlyYear] = useState<number | null>(null);

  // Пользовательский процент для налога (по умолчанию 1%)
  const [taxPercentInput, setTaxPercentInput] = useState("1");
  const [taxPercent, setTaxPercent] = useState(1);
  const rawPlan = (user?.plan ?? "trial").trim().toLowerCase();
  const isTrial10 = !user?.is_admin && (!rawPlan || rawPlan === "trial");
  const isSubscriptionActive =
    !!user?.is_admin ||
    (typeof user?.trial_days_left === "number" && user.trial_days_left > 0);

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

  const minYear = salesMinDate ? new Date(salesMinDate).getFullYear() : null;
  const maxYear = salesMaxDate ? new Date(salesMaxDate).getFullYear() : null;

  useEffect(() => {
    if (monthlyYear == null && maxYear != null) {
      setMonthlyYear(maxYear);
    }
  }, [monthlyYear, maxYear]);

  const qtyUnit = t('common.pieces');
  const salesMetrics = metrics ? [
    {
      icon: <ShoppingCart className="w-4 h-4" />,
      label: t('summary.sales.orders'),
      value: formatQuantity(metrics.ordersCount, qtyUnit),
      subValue: formatCurrency(metrics.ordersValue),
      tooltip: t('summary.sales.ordersTooltip')
    },
    {
      icon: <Truck className="w-4 h-4" />,
      label: t('summary.sales.processing'),
      value: formatQuantity(metrics.processingCount, qtyUnit),
      subValue: formatCurrency(metrics.processingValue),
      tooltip: t('summary.sales.processingTooltip')
    },
    {
      icon: <Package className="w-4 h-4" />,
      label: t('summary.sales.completed'),
      value: formatQuantity(metrics.completedCount, qtyUnit),
      subValue: formatCurrency(metrics.completedValue),
      tooltip: t('summary.sales.completedTooltip')
    },
    {
      icon: <RotateCcw className="w-4 h-4" />,
      label: t('summary.sales.returns'),
      value: formatQuantity(metrics.returnsCount, qtyUnit),
      subValue: metrics.returnsValue > 0 ? `-${formatCurrency(metrics.returnsValue)}` : formatCurrency(0),
      tooltip: t('summary.sales.returnsTooltip')
    },
    {
      icon: <Percent className="w-4 h-4" />,
      label: t('summary.sales.returnRate'),
      value: formatPercent(metrics?.returnRate),
      tooltip: t('summary.sales.returnRateTooltip')
    },
    {
      icon: <CreditCard className="w-4 h-4" />,
      label: t('summary.sales.averageCheck'),
      value: formatMoneyNoDecimals(metrics.averageCheck),
      tooltip: t('summary.sales.averageCheckTooltip')
    }
  ] : [];

  const financeMetrics = metrics ? [
    {
      icon: <DollarSign className="w-4 h-4" />,
      label: t('summary.finance.revenue'),
      value: formatCurrency(metrics.revenue),
      tooltip: t('summary.finance.revenueTooltip')
    },
    {
      icon: <TrendingDown className="w-4 h-4" />,
      label: t('summary.finance.expenses'),
      value: formatCurrency(adjustedTotalExpenses),
      tooltip: t('summary.finance.expensesTooltip')
    },
    {
      icon: <Wallet className="w-4 h-4" />,
      label: t('summary.finance.profit'),
      value: formatCurrency(adjustedProfit),
      tooltip: t('summary.finance.profitTooltip')
    },
    {
      icon: <Target className="w-4 h-4" />,
      label: t('summary.finance.salesProfitability'),
      value: formatPercent(adjustedSalesProfitability),
      tooltip: t('summary.finance.salesProfitabilityTooltip')
    },
    {
      icon: <BarChart3 className="w-4 h-4" />,
      label: t('summary.finance.roi'),
      value: formatPercent(adjustedRoi),
      tooltip: t('summary.finance.roiTooltip')
    },
    {
      icon: <TrendingUp className="w-4 h-4" />,
      label: t('summary.finance.revenueTrend'),
      value: formatTrend(metrics.revenueTrend),
      trend: (metrics.revenueTrend ?? 0) >= 0 ? "up" as const : "down" as const,
      trendValue: "",
      tooltip: t('summary.finance.revenueTrendTooltip')
    }
  ] : [];

  // Основные метрики расходов (зависят от выбранного магазина)
  const expenseMetrics = metrics ? [
    {
      icon: <Percent className="w-4 h-4" />,
      label: t('summary.expense.commissionUzum'),
      value: formatCurrency(metrics.uzumCommission),
      tooltip: ""
    },
    {
      icon: <Truck className="w-4 h-4" />,
      label: t('summary.expense.logisticsUzum'),
      value: formatCurrency(metrics.uzumLogistics),
      tooltip: ""
    },
    {
      icon: <Boxes className="w-4 h-4" />,
      label: t('summary.expense.productCost'),
      value: formatCurrency(metrics.productCost),
      tooltip: ""
    },
    {
      icon: <Receipt className="w-4 h-4" />,
      label: (
        <div className="flex items-center gap-1">
          <span>{t('summary.expense.taxes')}</span>
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
      label: t('summary.expense.extraExpenses'),
      value: formatCurrency(metrics.extraExpenses),
      tooltip: t('summary.expense.extraExpensesTooltip')
    }
  ] : [];

  // Метрики услуг UZUM (не зависят от выбранного магазина)
  // Порядок: Хранение, Реклама, Штрафы (как на скриншоте)
  const uzumServicesMetrics = metrics ? [
    {
      icon: <Warehouse className="w-4 h-4" />,
      label: t('summary.uzum.storage'),
      value: formatCurrency(metrics.uzumStorage),
      tooltip: t('summary.uzum.storageTooltip')
    },
    {
      icon: <Target className="w-4 h-4" />,
      label: t('summary.uzum.ads'),
      value: formatCurrency(metrics.uzumAds),
      tooltip: t('summary.uzum.adsTooltip')
    },
    {
      icon: <AlertTriangle className="w-4 h-4" />,
      label: t('summary.uzum.fines'),
      value: formatCurrency(metrics.uzumFines),
      tooltip: t('summary.uzum.finesTooltip')
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
      label: t('summary.warehouse.stock'),
      value: formatQuantity(stockQty, qtyUnit),
      tooltip: t('summary.warehouse.stockTooltip')
    },
    {
      icon: <Tag className="w-4 h-4" />,
      label: t('summary.warehouse.cost'),
      value: formatCurrency(stockCost),
      tooltip: ""
    },
    {
      icon: <ShoppingBag className="w-4 h-4" />,
      label: t('summary.warehouse.retailPrice'),
      value: formatCurrency(stockRetail),
      tooltip: t('summary.warehouse.retailPriceTooltip')
    }
  ] : [];

  return (
    <MainLayout>
      {/* Header with title and actions */}
      <div className="flex flex-col gap-4 mb-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <img
                  src="/favicon.png"
                  alt=""
                  className="h-6 w-6 flex-shrink-0 object-contain"
                />
                <h1 className="text-xl font-semibold text-foreground">
                  <span className="font-bold">PROFi</span>
                  <span className="font-normal">board</span>
                </h1>
              </div>
            </div>
            {(salesMinDate && salesMaxDate) || lastUpdatedAt ? (() => {
              const formatShortDate = (dateStr: string) => {
                const [, month, day] = dateStr.split("-");
                return `${day}.${month}`;
              };
              const formatDateTime = (iso: string) => {
                const date = new Date(iso);
                const day = String(date.getDate()).padStart(2, "0");
                const month = String(date.getMonth() + 1).padStart(2, "0");
                const hours = String(date.getHours()).padStart(2, "0");
                const minutes = String(date.getMinutes()).padStart(2, "0");
                return `${day}.${month}, ${hours}:${minutes}`;
              };
              const next = getNextUzumSyncSchedule();
              return (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="flex flex-col gap-0.5 pl-1 text-xs text-muted-foreground/80 cursor-default">
                      {salesMinDate && salesMaxDate && (
                        <div>
                          {t("common.dataPeriod")}{" "}
                          <span className="font-medium">
                            {formatShortDate(salesMinDate)}–{formatShortDate(salesMaxDate)}
                          </span>
                        </div>
                      )}
                      {lastUpdatedAt && (
                        <div>
                          {t("common.lastUpdate")}{" "}
                          <span className="font-medium">{formatDateTime(lastUpdatedAt)}</span>
                        </div>
                      )}
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="bottom" align="start" className="text-sm">
                    {isSubscriptionActive ? (
                      <>
                        {t("common.nextUpdate")}{" "}
                        <span className="font-medium">
                          {next.dateLabel}, {next.timeLabel}
                        </span>
                      </>
                    ) : (
                      t("common.renewTariffForUpdate")
                    )}
                  </TooltipContent>
                </Tooltip>
              );
            })() : null}
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
            <HeaderActions apiConnectRef={apiConnectRef} />
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

      {isTrial10 && (
        <div className="mt-8 flex justify-center">
          <div className="inline-block rounded-md border border-amber-300/80 bg-amber-50 px-4 py-3 text-center text-sm text-amber-900">
            {language === "uz"
              ? "Trial: faqat oxirgi 60 kunlik ma'lumotlar ko'rsatiladi. To'liq davr va barcha do'konlar Month 5 va Month 10 tariflarida mavjud."
              : "Trial: отображаются данные за последние 60 дней. Полный период и все магазины доступны на тарифах Month 5 и Month 10."}
          </div>
        </div>
      )}

      {/* Tabs и фильтры на одном уровне */}
      <div className={`flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${isTrial10 ? "mt-6" : "mt-14"}`}>
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

      {activeTab === "summary" && (
        <SummaryWeeklyInsights
          referenceDate={salesMaxDate ?? maxDate ?? dateTo}
          shop={selectedShop}
          onOpenUploadReports={openApiConnect}
          onOpenProduct={(entry: WeeklyInsightProduct) => {
            const referenceDate = salesMaxDate ?? maxDate ?? dateTo;
            if (referenceDate) {
              const { lastWeekFrom, lastWeekTo } = getWeeklyInsightRanges(referenceDate);
              setDateRange({ dateFrom: lastWeekFrom, dateTo: lastWeekTo });
            }
            setProductToOpen(entry.item);
            setActiveTab("products");
          }}
        />
      )}

      {/* Content based on active tab */}
      {activeTab === "monthly" ? (
        <div className="mt-6">
          <MonthlyTable
            year={monthlyYear ?? (maxYear ?? new Date().getFullYear())}
            shop={null}
            taxPercent={taxPercent}
            yearSwitcher={
              minYear != null && maxYear != null ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <button
                    type="button"
                    className="px-2 py-1 rounded border border-border disabled:opacity-40"
                    onClick={() =>
                      setMonthlyYear((prev) =>
                        prev && minYear ? Math.max(minYear, prev - 1) : prev
                      )
                    }
                    disabled={monthlyYear == null || monthlyYear <= minYear}
                  >
                    ‹
                  </button>
                  <span>
                    {monthlyYear ?? (maxYear ?? new Date().getFullYear())}
                  </span>
                  <button
                    type="button"
                    className="px-2 py-1 rounded border border-border disabled:opacity-40"
                    onClick={() =>
                      setMonthlyYear((prev) =>
                        prev && maxYear ? Math.min(maxYear, prev + 1) : prev
                      )
                    }
                    disabled={monthlyYear == null || monthlyYear >= maxYear}
                  >
                    ›
                  </button>
                </div>
              ) : null
            }
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
          <ProductsView
            shop={selectedShop}
            taxPercent={taxPercent}
            dateFrom={dateFrom}
            dateTo={dateTo}
            openProduct={productToOpen}
            onOpenProductHandled={handleOpenProductHandled}
          />
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
                <SummaryBlock title={t('summary.blockSales')} titleColor="text-chart-4" metrics={salesMetrics} />
                <SummaryBlock title={t('summary.blockFinances')} titleColor="text-warning" metrics={financeMetrics} />
                <SummaryBlock 
                  title={t('summary.blockExpenses')} 
                  titleColor="text-destructive" 
                  metrics={expenseMetrics} 
                />
                <div className="flex flex-col h-full gap-4">
                  <SummaryBlock 
                    title={t('summary.blockWarehouse')} 
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
                          <AlertTitle>{t('alert.stockZero')}</AlertTitle>
                          <AlertDescription>
                            <p className="mb-2">
                              {stockZeroReason === "all_zero_in_snapshot"
                                ? t('alert.stockZeroReasonAll')
                                : t('alert.stockZeroDesc')}
                            </p>
                            {(stockSkuTotal > 0 || stockSkuWithStock >= 0 || stockSnapshotAt) && (
                              <div className="text-xs text-muted-foreground space-y-1">
                                {stockSkuTotal > 0 && (
                                  <p>SKU: {stockSkuTotal}, с остатком: {stockSkuWithStock}</p>
                                )}
                                {stockSnapshotAt && (
                                  <p>{t('common.snapshot')}: {new Date(stockSnapshotAt).toLocaleString("ru-RU")}</p>
                                )}
                              </div>
                            )}
                          </AlertDescription>
                        </Alert>
                      ) : !loading && !stockHasData && stockSource === null ? (
                        <p className="text-sm text-muted-foreground m-0">{t('alert.noStockData')}</p>
                      ) : undefined
                    }
                  />
                  <SummaryBlock 
                    title={t('summary.blockUzumServices')} 
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
