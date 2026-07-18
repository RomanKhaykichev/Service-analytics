import { ChevronRight, Package as PackageIcon, MessageSquare } from "lucide-react";
import { useState, useEffect } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, buildQueryParams } from "@/lib/api";
import { toast } from "sonner";
import { ShoppingCart, Truck, Package, RotateCcw, Percent, CreditCard, DollarSign, TrendingDown, Wallet, Target, BarChart3, TrendingUp, ArrowDown, Receipt, Boxes, Warehouse, Tag, ShoppingBag, Info } from "lucide-react";
import { SummaryBlock } from "./SummaryBlock";
import { RevenueDailyChart } from "./RevenueDailyChart";
import { useRevenueDaily } from "@/hooks/useRevenueDaily";
import { formatCurrency, formatQuantity, formatPercent, formatTrend, formatMoneyNoDecimals } from "@/lib/formatters";
import { useDashboardMetrics } from "@/hooks/useDashboardMetrics";
import { useLanguage } from "@/contexts/LanguageContext";
import { getSizeGroupColorClass } from "@/lib/utils";
import { ProductThumbnail } from "@/components/dashboard/ProductThumbnail";

function formatProductRatingLine(
  rating: number | null | undefined,
  feedbackQuantity: number | null | undefined,
  ratingPrefix: string,
): string | null {
  if (rating == null && feedbackQuantity == null) return null;
  const ratingValue = rating != null ? rating.toFixed(1) : "—";
  const count = feedbackQuantity ?? 0;
  return `${ratingPrefix} ${ratingValue} (${count}) ⭐️`;
}

interface ProductVariant {
  char1: string; // Хар-ка 1 = 3 часть из SKU
  char2: string; // Хар-ка 2 = 4 часть из SKU
  char3: string; // Хар-ка 3 = 5 часть из SKU
  sales_qty: number; // Заказы
  stock: number | null; // Остатки FBO
  fbs_stock: number | null; // Остатки FBS
  size_group: string | null; // Габ. группа
  barcode: string | null; // Штрихкод
  storage_cost_per_day: number | null; // Хранение сут/сум
}
interface Product {
  id: string;
  name: string;
  article: string;
  price: number;
  sales: number;
  returns: number;
  ordersValue: number;
  processingQty: number;
  processingValue: number;
  completedQty: number;
  completedValue: number;
  returnsValue: number;
  revenue: number;
  lostRevenue: number;
  turnover: number;
  stock: number;
  fbsStock: number;
  endsIn: string;
  costPrice: number | null;
  /** Себест. за ед. на складе FBO (Profiboard / left-out), как на Сводке */
  stockUnitCogs?: number | null;
  /** Сумма себестоимости склада FBO по вариантам (stock_unit_cogs × «В продаже») */
  stockCogsLine?: number | null;
  /** Сумма себестоимости (cogs_sum × qty) по завершённым — для блока Расходы как на Сводке */
  cogsTotal: number;
  uzumCommission: number;
  uzumLogistics: number;
  /** Прибыль по формуле Сводки: выручка − расходы (в т.ч. налог с вкладки Сводка) */
  profit: number;
  abcOrders: string;
  abcProfit: string;
  abcRevenue: string;
  barcode: string;
  brand: string;
  category: string;
  status: string;
  product_image_url?: string | null;
  rating?: number | null;
  feedback_quantity?: number | null;
}
interface ProductDetailViewProps {
  product: Product;
  variants?: Array<{
    sku: string | null;
    sales_qty: number;
    stock: number | null;
    fbs_stock?: number | null;
    size_group: string | null;
    barcode: string | null;
    storage_cost_per_day: number | null;
    cogs?: number | null;
    stock_unit_cogs?: number | null;
    stock_cogs_line?: number | null;
    price?: number | null;
  }>;
  onBack: () => void;
  /** Пользовательский процент налога (из вкладки Сводка). По умолчанию 1. */
  taxPercent?: number;
  /** Период для расчёта тренда выручки (как на Сводке: сравнение с предыдущим периодом той же длины) */
  dateFrom?: string;
  dateTo?: string;
  /** Общая выручка (все товары) для расчёта «От общей выручки» = выручка по ID / общая выручка */
  totalRevenue?: number;
}
interface ProductCommentResponse {
  product_id: string;
  comment: string | null;
}

export function ProductDetailView({
  product,
  variants = [],
  onBack,
  taxPercent = 1,
  dateFrom,
  dateTo,
  totalRevenue: totalRevenueProp = 0,
}: ProductDetailViewProps) {
  const { t } = useLanguage();
  const [comment, setComment] = useState("");
  const queryClient = useQueryClient();

  // Предыдущий период (та же длина, сразу перед текущим) — как на Сводке для тренда выручки
  const prevPeriod = (() => {
    if (!dateFrom || !dateTo) return null;
    try {
      const from = new Date(dateFrom);
      const to = new Date(dateTo);
      const days = Math.round((to.getTime() - from.getTime()) / (24 * 60 * 60 * 1000)) + 1;
      const prevTo = new Date(from);
      prevTo.setDate(prevTo.getDate() - 1);
      const prevFrom = new Date(prevTo);
      prevFrom.setDate(prevFrom.getDate() - days + 1);
      return {
        dateFrom: prevFrom.toISOString().slice(0, 10),
        dateTo: prevTo.toISOString().slice(0, 10),
      };
    } catch {
      return null;
    }
  })();

  // Выручка за предыдущий период по этому товару (ID карточки) — для тренда выручки (как на Сводке)
  const { data: prevPeriodData } = useQuery({
    queryKey: ["products-table-prev", prevPeriod?.dateFrom, prevPeriod?.dateTo, product.id],
    queryFn: async () => {
      const params = buildQueryParams({
        date_from: prevPeriod!.dateFrom,
        date_to: prevPeriod!.dateTo,
      });
      const data = await apiGet<{ items: Array<{ product_id?: string; sku?: string; barcode?: string; revenue?: number }> }>(
        "/api/charts/products-table",
        params
      );
      return data?.items ?? [];
    },
    enabled: !!prevPeriod?.dateFrom && !!prevPeriod?.dateTo && !!product.id,
    refetchOnWindowFocus: false,
  });

  const prevRevenue = (() => {
    if (!prevPeriodData?.length || !product.id) return 0;
    const productId = product.id;
    const items = prevPeriodData.filter(
      (p) => (p.product_id || p.sku || p.barcode) === productId
    );
    return items.reduce((sum, p) => sum + (p.revenue ?? 0), 0);
  })();

  const revenueTrend =
    prevRevenue > 0 ? ((product.revenue - prevRevenue) / prevRevenue) * 100 : 0;

  // Маржинальность и От общей выручки — по всей выгрузке (без привязки к фильтру по датам)
  const { data: allTimeMetrics } = useQuery({
    queryKey: ["product-card-all-time-metrics", product.id],
    queryFn: async () => {
      const params = buildQueryParams({ product_id: product.id });
      return apiGet<{ revenue: number; profit: number; total_revenue: number }>(
        "/api/charts/product-card-all-time-metrics",
        params
      );
    },
    enabled: !!product.id,
    refetchOnWindowFocus: false,
  });
  const allTimeRevenue = allTimeMetrics?.revenue ?? 0;
  const allTimeProfit = allTimeMetrics?.profit ?? 0;
  const allTimeTotalRevenue = allTimeMetrics?.total_revenue ?? 0;
  const marginPercentAllTime = allTimeRevenue > 0 ? (allTimeProfit / allTimeRevenue) * 100 : 0;
  const revenueSharePercentAllTime = allTimeTotalRevenue > 0 ? (allTimeRevenue / allTimeTotalRevenue) * 100 : 0;

  // Продажи по дням — данные по ID карточки; ось X = выбранный диапазон дат (dateFrom–dateTo)
  const { points: revenueDailyPoints } = useRevenueDaily({
    dateFrom: dateFrom ?? "",
    dateTo: dateTo ?? "",
    productId: product.id || null,
  });
  const revenueChartData = (() => {
    if (!dateFrom || !dateTo) return undefined;
    const from = new Date(dateFrom);
    const to = new Date(dateTo);
    const pointsByDate = new Map<string, { revenue: number; orders: number; avgCheck: number; returns?: number; profit?: number }>();
    for (const p of revenueDailyPoints) {
      const key = (p.date || "").slice(0, 10);
      if (key) pointsByDate.set(key, {
        revenue: p.revenue ?? 0,
        orders: p.orders ?? 0,
        avgCheck: p.averageCheck ?? 0,
        returns: p.returns,
        profit: p.profit,
      });
    }
    const result: Array<{ date: string; revenue: number; orders: number; avgCheck: number; returns?: number; profit?: number }> = [];
    const cursor = new Date(from);
    while (cursor <= to) {
      const key = cursor.toISOString().slice(0, 10);
      const day = String(cursor.getDate()).padStart(2, "0");
      const month = String(cursor.getMonth() + 1).padStart(2, "0");
      const point = pointsByDate.get(key);
      result.push({
        date: `${day}.${month}`,
        revenue: point?.revenue ?? 0,
        orders: point?.orders ?? 0,
        avgCheck: point?.avgCheck ?? 0,
        returns: point?.returns,
        profit: point?.profit,
      });
      cursor.setDate(cursor.getDate() + 1);
    }
    return result;
  })();

  // Загружаем комментарий при открытии карточки
  const { data: commentData } = useQuery({
    queryKey: ["product-comment", product.id],
    queryFn: async () => {
      return apiGet<ProductCommentResponse>(`/api/products/${encodeURIComponent(product.id)}/comment`);
    },
    refetchOnWindowFocus: false,
  });

  // Обновляем локальное состояние комментария при загрузке данных
  useEffect(() => {
    if (commentData) {
      setComment(commentData.comment || "");
    }
  }, [commentData]);

  // Мутация для сохранения комментария
  const saveCommentMutation = useMutation({
    mutationFn: async (commentText: string) => {
      const trimmedComment = commentText.trim();
      return apiPost<ProductCommentResponse>(
        `/api/products/${encodeURIComponent(product.id)}/comment`,
        {
          product_id: product.id,
          comment: trimmedComment || null,
        }
      );
    },
    onSuccess: (data) => {
      // Обновляем локальное состояние комментария после сохранения
      setComment(data.comment || "");
      queryClient.invalidateQueries({ queryKey: ["product-comment", product.id] });
      toast.success("Комментарий сохранен");
    },
    onError: (error: any) => {
      console.error("Error saving comment:", error);
      const errorMessage = error?.message || error?.toString() || "Неизвестная ошибка";
      toast.error(t('product.saveCommentError').replace('{0}', errorMessage));
    },
  });

  const handleSaveComment = () => {
    saveCommentMutation.mutate(comment);
  };

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat("ru-RU").format(price) + " " + t("common.sum");
  };
  const formatNumber = (num: number) => {
    return new Intl.NumberFormat("ru-RU").format(num);
  };

  // Преобразуем варианты товара в формат для таблицы
  const productVariants: ProductVariant[] = variants.map(v => {
    // Разбиваем SKU по дефисам
    const skuParts = (v.sku || "").split("-").map(p => p.trim()).filter(p => p.length > 0);
    
    return {
      char1: skuParts[2] || "—", // 3 часть (индекс 2)
      char2: skuParts[3] || "—", // 4 часть (индекс 3)
      char3: skuParts[4] || "—", // 5 часть (индекс 4)
      sales_qty: v.sales_qty,
      stock: v.stock,
      fbs_stock: v.fbs_stock ?? null,
      size_group: v.size_group,
      barcode: v.barcode,
      storage_cost_per_day: v.storage_cost_per_day,
    };
  });

  // Determine product type: первые 2 части после разбивки на дефисы
  const getProductType = () => {
    if (!product.article) return "—";
    
    // Разбиваем по дефисам
    const parts = product.article.split("-").map(p => p.trim()).filter(p => p.length > 0);
    if (parts.length === 0) return "—";
    
    // Берем первые 2 части и объединяем дефисом
    const firstTwoParts = parts.slice(0, 2).join(" - ");
    return firstTwoParts || "—";
  };
  // Блоки как на вкладке Сводка: те же формулы по ID карточки (агрегат по всем вариантам)
  const ordersQty = product.sales;
  const ordersValue = product.ordersValue;
  const processingQty = product.processingQty;
  const processingValue = product.processingValue;
  const completedQty = product.completedQty;
  const completedValue = product.completedValue;
  const returnsValueNum = product.returnsValue;
  const returnRate = ordersQty > 0 ? (product.returns / ordersQty) * 100 : 0;
  const qtyForAvgCheck = completedQty + processingQty;
  const revenueForAvgCheck = completedValue + processingValue;
  const averageCheck = qtyForAvgCheck > 0 ? Math.round(revenueForAvgCheck / qtyForAvgCheck) : 0;
  // Доп. расходы для этого товара (по наименованию) — как на вкладке Сводка с учетом ID карточки
  const { data: productExtraExpensesData } = useQuery({
    queryKey: ["kpiSummary-product-extra", dateFrom, dateTo, product.name],
    queryFn: async () => {
      const params = buildQueryParams({ 
        date_from: dateFrom ?? undefined, 
        date_to: dateTo ?? undefined,
        name: product.name ?? undefined
      });
      return apiGet<{ extraExpenses: number }>("/api/kpi/summary", params);
    },
    enabled: !!dateFrom && !!dateTo && !!product.name,
    refetchOnWindowFocus: false,
  });
  const productExtraExpenses = productExtraExpensesData?.extraExpenses ?? 0;

  const taxAmount = product.revenue * (taxPercent / 100);
  const totalExpenses = product.uzumCommission + product.uzumLogistics + product.cogsTotal + taxAmount + productExtraExpenses;
  // Прибыль = Выручка − Расходы (включая доп. расходы), как на Сводке
  const profit = product.revenue - totalExpenses;
  const salesProfitability = product.revenue > 0 ? (profit / product.revenue) * 100 : 0;
  const roi = totalExpenses > 0 ? (profit / totalExpenses) * 100 : 0;
  const revenueSharePercent = totalRevenueProp > 0 ? (product.revenue / totalRevenueProp) * 100 : 0;
  // Себест. тов. = сумма stock_cogs_line по вариантам (как СКЛАД UZUM на Сводке), иначе stockUnitCogs × stock
  const stockCost =
    variants.length > 0
      ? variants.reduce(
          (sum, v) =>
            sum +
            (v.stock_cogs_line ??
              (v.stock_unit_cogs ?? 0) * (v.stock ?? 0)),
          0
        )
      : product.stockCogsLine ??
        (product.stockUnitCogs ?? product.costPrice ?? 0) * product.stock;
  const stockRetail =
    variants.length > 0
      ? variants.reduce(
          (sum, v) => sum + (v.price ?? 0) * (v.stock ?? 0),
          0
        )
      : product.price * product.stock;

  const ratingLine = formatProductRatingLine(
    product.rating,
    product.feedback_quantity,
    t("product.ratingPrefix"),
  );

  const qtyUnit = t('common.pieces');
  const salesMetrics = [
    { icon: <ShoppingCart className="w-4 h-4" />, label: t('summary.sales.orders'), value: formatQuantity(ordersQty, qtyUnit), subValue: formatCurrency(ordersValue), tooltip: t('summary.sales.ordersTooltip') },
    { icon: <Truck className="w-4 h-4" />, label: t('summary.sales.processing'), value: formatQuantity(processingQty, qtyUnit), subValue: formatCurrency(processingValue), tooltip: t('summary.sales.processingTooltip') },
    { icon: <Package className="w-4 h-4" />, label: t('summary.sales.completed'), value: formatQuantity(completedQty, qtyUnit), subValue: formatCurrency(completedValue), tooltip: t('summary.sales.completedTooltip') },
    { icon: <RotateCcw className="w-4 h-4" />, label: t('summary.sales.returns'), value: formatQuantity(product.returns, qtyUnit), subValue: product.returns > 0 ? `-${formatCurrency(returnsValueNum)}` : formatCurrency(0), tooltip: t('summary.sales.returnsTooltip') },
    { icon: <Percent className="w-4 h-4" />, label: t('summary.sales.returnRate'), value: formatPercent(returnRate), tooltip: t('summary.sales.returnRateTooltip') },
    { icon: <CreditCard className="w-4 h-4" />, label: t('summary.sales.averageCheck'), value: formatMoneyNoDecimals(averageCheck), tooltip: t('summary.sales.averageCheckTooltip') },
  ];
  const financeMetrics = [
    { icon: <DollarSign className="w-4 h-4" />, label: t('summary.finance.revenue'), value: formatCurrency(product.revenue), tooltip: t('summary.finance.revenueTooltip') },
    { icon: <TrendingDown className="w-4 h-4" />, label: t('summary.finance.expenses'), value: formatCurrency(totalExpenses), tooltip: t('summary.finance.expensesTooltip') },
    { icon: <Wallet className="w-4 h-4" />, label: t('summary.finance.profit'), value: formatCurrency(profit), tooltip: t('summary.finance.profitTooltip') },
    { icon: <Target className="w-4 h-4" />, label: t('summary.finance.salesProfitability'), value: formatPercent(salesProfitability), tooltip: t('summary.finance.salesProfitabilityTooltip') },
    { icon: <BarChart3 className="w-4 h-4" />, label: t('summary.finance.roi'), value: formatPercent(roi), tooltip: t('summary.finance.roiTooltip') },
    { icon: <TrendingUp className="w-4 h-4" />, label: t('summary.finance.revenueTrend'), value: formatTrend(revenueTrend), trend: (revenueTrend >= 0 ? "up" : "down") as const, trendValue: "", tooltip: t('summary.finance.revenueTrendTooltip') },
  ];
  const expenseMetrics = [
    { icon: <Percent className="w-4 h-4" />, label: t('summary.expense.commissionUzum'), value: formatCurrency(product.uzumCommission), tooltip: "" },
    { icon: <Truck className="w-4 h-4" />, label: t('summary.expense.logisticsUzum'), value: formatCurrency(product.uzumLogistics), tooltip: "" },
    { icon: <Boxes className="w-4 h-4" />, label: t('summary.expense.productCost'), value: formatCurrency(product.cogsTotal), tooltip: "" },
    { icon: <Receipt className="w-4 h-4" />, label: t('summary.expense.taxes'), value: formatCurrency(taxAmount), tooltip: "" },
    { icon: <Info className="w-4 h-4" />, label: t('summary.expense.extraExpenses'), value: formatCurrency(productExtraExpenses), tooltip: t('summary.expense.extraExpensesTooltip') },
  ];
  const warehouseMetrics = [
    { icon: <Warehouse className="w-4 h-4" />, label: t('summary.warehouse.stock'), value: formatQuantity(product.stock, qtyUnit), tooltip: t('summary.warehouse.stockTooltip') },
    { icon: <Tag className="w-4 h-4" />, label: t('summary.warehouse.cost'), value: formatCurrency(stockCost), tooltip: "" },
    { icon: <ShoppingBag className="w-4 h-4" />, label: t('summary.warehouse.retailPrice'), value: formatCurrency(stockRetail), tooltip: t('summary.warehouse.retailPriceTooltip') },
  ];
  const fbsWarehouseMetrics = [
    { icon: <Warehouse className="w-4 h-4" />, label: t('summary.warehouse.stock'), value: formatQuantity(product.fbsStock, qtyUnit), tooltip: t('summary.warehouse.fbsStockTooltip') },
  ];

  return <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1 text-sm">
        <button onClick={onBack} className="text-primary hover:text-primary/80 transition-colors font-medium">
          {t('product.products')}
        </button>
        <ChevronRight className="w-4 h-4 text-muted-foreground" />
        <span className="text-foreground font-medium truncate max-w-[300px]">
          {product.name}
        </span>
      </nav>

      {/* Product Info Block */}
      <div className="bg-card border border-border rounded-lg p-6">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-2">
            <PackageIcon className="w-5 h-5 text-primary" />
            <h2 className="text-lg font-semibold text-foreground">{t('product.productTitle')}</h2>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center rounded-md px-3 py-1.5 text-sm font-medium bg-green-100 text-green-800 dark:bg-green-950/50 dark:text-green-400">
              {t('product.marginality')}: {marginPercentAllTime.toFixed(1)}%
            </span>
            <span className="inline-flex items-center rounded-md px-3 py-1.5 text-sm font-medium bg-violet-100 text-violet-800 dark:bg-violet-950/50 dark:text-violet-400">
              {t('product.revenueShare')}: {revenueSharePercentAllTime.toFixed(1)}%
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Part - Product Details */}
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div className="col-span-2 space-y-4">
                <div>
                  <span className="text-sm text-muted-foreground">{t('product.name')}</span>
                  <p className="text-foreground font-medium">{product.name}</p>
                </div>
                <div>
                  <span className="text-sm text-muted-foreground">{t('product.productType')}</span>
                  <p className="text-foreground font-medium">{getProductType()}</p>
                </div>
                <div>
                  <span className="text-sm text-muted-foreground">{t('product.productId')}</span>
                  <p className="text-foreground font-medium font-mono">{product.id}</p>
                </div>
              </div>
              <div className="col-span-1 flex flex-col items-end justify-start gap-2 pr-1">
                {ratingLine && (
                  <p className="text-sm text-muted-foreground text-right">{ratingLine}</p>
                )}
                <ProductThumbnail
                  imageUrl={product.product_image_url}
                  alt={product.name}
                  fit="contain"
                  frame={false}
                  className="h-auto max-h-40 w-auto max-w-[10rem] rounded-lg"
                  placeholderClassName="h-28 w-28"
                />
              </div>
            </div>

            {/* Comment Block */}
            <div className="pt-4 border-t border-border">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">{t('product.comment')}</span>
                </div>
                <span className={`text-xs ${comment.length > 120 ? "text-destructive" : "text-muted-foreground"}`}>
                  {comment.length}/120
                </span>
              </div>
              <Textarea 
                placeholder={t('product.commentPlaceholder')} 
                value={comment} 
                onChange={e => {
                  const newValue = e.target.value;
                  if (newValue.length <= 120) {
                    setComment(newValue);
                  }
                }}
                className="min-h-[80px] resize-none" 
                maxLength={120}
              />
              <Button 
                size="sm" 
                className="mt-2" 
                disabled={saveCommentMutation.isPending}
                onClick={handleSaveComment}
              >
                {saveCommentMutation.isPending ? t('product.saving') : t('product.save')}
              </Button>
            </div>
          </div>

          {/* Right Part - Variants Table */}
          <div>
            <div className="bg-muted/30 rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th colSpan={3} className="px-3 py-2 text-left text-muted-foreground font-medium">{t('product.params')}</th>
                    <th className="px-3 py-2 text-center text-muted-foreground font-medium">{t('product.orders')}</th>
                    <th className="px-3 py-2 text-center text-muted-foreground font-medium">{t('product.stockFbo')}</th>
                    <th className="px-3 py-2 text-center text-muted-foreground font-medium">{t('product.stockFbs')}</th>
                    <th className="px-3 py-2 text-center text-muted-foreground font-medium">{t('product.sizeGroup')}</th>
                    <th className="px-3 py-2 text-center text-muted-foreground font-medium">{t('product.barcode')}</th>
                    <th className="px-3 py-2 text-center text-muted-foreground font-medium">
                      <div className="flex flex-col items-center">
                        <span>{t('product.storage')}</span>
                        <span className="text-xs">{t('product.storageDaySum')}</span>
                      </div>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {productVariants.length > 0 ? (
                    productVariants.map((variant, index) => {
                      return (
                        <tr key={index} className={index !== productVariants.length - 1 ? "border-b border-border/50" : ""}>
                          <td className="px-3 py-2 text-left text-foreground">{variant.char1}</td>
                          <td className="px-3 py-2 text-left text-foreground">{variant.char2}</td>
                          <td className="px-3 py-2 text-left text-foreground">{variant.char3}</td>
                          <td className="px-3 py-2 text-center text-foreground font-medium">{formatNumber(variant.sales_qty)}</td>
                          <td className="px-3 py-2 text-center text-foreground">{variant.stock != null ? formatNumber(variant.stock) : "—"}</td>
                          <td className="px-3 py-2 text-center text-foreground">{variant.fbs_stock != null ? formatNumber(variant.fbs_stock) : "—"}</td>
                          <td className="px-3 py-2 text-center">
                            {variant.size_group && variant.size_group !== "-" ? (
                              <span className={`px-2 py-0.5 rounded text-xs font-medium ${getSizeGroupColorClass(variant.size_group)}`}>
                                {variant.size_group}
                              </span>
                            ) : (
                              <span className="text-muted-foreground">—</span>
                            )}
                          </td>
                          <td className="px-3 py-2 text-center text-foreground font-mono text-xs">{variant.barcode || "—"}</td>
                          <td className="px-3 py-2 text-center text-foreground">
                            {variant.storage_cost_per_day != null ? formatNumber(variant.storage_cost_per_day) : "—"}
                          </td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan={9} className="px-3 py-4 text-center text-muted-foreground">
                        {t('product.noVariants')}
                      </td>
                    </tr>
                  )}
                </tbody>
                {productVariants.length > 0 && (
                  <tfoot>
                    <tr className="border-t border-border bg-muted/50">
                      <td colSpan={3} className="px-3 py-2 text-left text-foreground font-medium">{t('product.total')}</td>
                      <td className="px-3 py-2 text-center text-foreground font-semibold">
                        {formatNumber(productVariants.reduce((sum, v) => sum + v.sales_qty, 0))}
                      </td>
                      <td className="px-3 py-2 text-center text-foreground font-semibold">
                        {formatNumber(productVariants.reduce((sum, v) => sum + (v.stock ?? 0), 0))}
                      </td>
                      <td className="px-3 py-2 text-center text-foreground font-semibold">
                        {formatNumber(productVariants.reduce((sum, v) => sum + (v.fbs_stock ?? 0), 0))}
                      </td>
                      <td></td>
                      <td></td>
                      <td className="px-3 py-2 text-center text-foreground font-semibold">
                        {formatNumber(productVariants.reduce((sum, v) => sum + (v.storage_cost_per_day ?? 0), 0))}
                      </td>
                    </tr>
                  </tfoot>
                )}
              </table>
            </div>
          </div>
        </div>
      </div>

      {/* 4 KPI Blocks */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 items-stretch">
        <SummaryBlock title={t('summary.blockSales')} titleColor="text-chart-4" metrics={salesMetrics} />
        <SummaryBlock title={t('summary.blockFinances')} titleColor="text-warning" metrics={financeMetrics} />
        <SummaryBlock title={t('summary.blockExpenses')} titleColor="text-destructive" metrics={expenseMetrics} />
        <div className="flex h-full min-h-0 w-full min-w-0 flex-col gap-4">
          <SummaryBlock
            title={t('summary.blockWarehouse')}
            titleColor="text-warning"
            metrics={warehouseMetrics}
            customHeightClass="h-auto shrink-0"
            customOverflowClass="overflow-visible"
          />
          <SummaryBlock
            title={t('summary.blockWarehouseFbs')}
            titleColor="text-warning"
            metrics={fbsWarehouseMetrics}
            customHeightClass="flex-1 min-h-0"
            customOverflowClass="overflow-visible"
          />
        </div>
      </div>

      {/* Продажи по дням — данные по выбранному периоду из фильтра дат */}
      {dateFrom && dateTo ? (
        <div className="mt-6">
          <RevenueDailyChart data={revenueChartData} hideAvgCheck key={`${dateFrom}-${dateTo}`} />
        </div>
      ) : (
        <div className="mt-6 rounded-xl border border-border bg-muted/30 p-6 text-center text-sm text-muted-foreground">
          {t('product.selectPeriod')}
        </div>
      )}
    </div>;
}