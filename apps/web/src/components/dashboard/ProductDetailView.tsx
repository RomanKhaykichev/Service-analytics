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
interface ProductVariant {
  char1: string; // Хар-ка 1 = 3 часть из SKU
  char2: string; // Хар-ка 2 = 4 часть из SKU
  char3: string; // Хар-ка 3 = 5 часть из SKU
  sales_qty: number; // Заказы
  stock: number | null; // Остатки
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
  revenue: number;
  lostRevenue: number;
  turnover: number;
  stock: number;
  endsIn: string;
  costPrice: number | null;
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
}
interface ProductDetailViewProps {
  product: Product;
  variants?: Array<{
    sku: string | null;
    sales_qty: number;
    stock: number | null;
    size_group: string | null;
    barcode: string | null;
    storage_cost_per_day: number | null;
    cogs?: number | null;
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
      toast.error(`Ошибка при сохранении комментария: ${errorMessage}`);
    },
  });

  const handleSaveComment = () => {
    saveCommentMutation.mutate(comment);
  };

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat("ru-RU").format(price) + " сум";
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
  // Блоки как на вкладке Сводка, но данные по ID карточки (агрегат по всем вариантам)
  const completedQty = Math.max(product.sales - product.returns, 0);
  const processingValue = 0; // цена В обработке
  const completedValue = product.revenue; // цена Выкупы
  const returnsValueNum = completedQty > 0 ? product.returns * (product.revenue / completedQty) : 0; // сумма возвратов (в формуле суммируется как положительное слагаемое)
  // Цена Заказов = цена В обработке + цена Выкупы + цена Возвраты (все три суммируются; возвраты в строке отображаются с минусом)
  const ordersValue = processingValue + completedValue + returnsValueNum;
  const returnRate = product.sales > 0 ? (product.returns / product.sales) * 100 : 0;
  const averageCheck = completedQty > 0 ? product.revenue / completedQty : product.sales > 0 ? product.revenue / product.sales : 0;
  const taxAmount = product.revenue * (taxPercent / 100);
  const totalExpenses = product.uzumCommission + product.uzumLogistics + product.cogsTotal + taxAmount + 0;
  const salesProfitability = product.revenue > 0 ? (product.profit / product.revenue) * 100 : 0;
  const roi = totalExpenses > 0 ? (product.profit / totalExpenses) * 100 : 0;
  const revenueSharePercent = totalRevenueProp > 0 ? (product.revenue / totalRevenueProp) * 100 : 0;
  // Себест. тов. = сумма по вариантам (себестоимость за ед. × остаток), иначе product.costPrice × product.stock
  const stockCost =
    variants.length > 0
      ? variants.reduce(
          (sum, v) => sum + (v.cogs ?? 0) * (v.stock ?? 0),
          0
        )
      : (product.costPrice ?? 0) * product.stock;
  const stockRetail =
    variants.length > 0
      ? variants.reduce(
          (sum, v) => sum + (v.price ?? 0) * (v.stock ?? 0),
          0
        )
      : product.price * product.stock;

  const salesMetrics = [
    { icon: <ShoppingCart className="w-4 h-4" />, label: "Заказы", value: formatQuantity(product.sales), subValue: formatCurrency(ordersValue), tooltip: "Цена Заказов = цена В обработке + цена Выкупы + цена Возвраты" },
    { icon: <Truck className="w-4 h-4" />, label: "В обработке", value: formatQuantity(0), subValue: formatCurrency(processingValue), tooltip: "Заказы в процессе обработки" },
    { icon: <Package className="w-4 h-4" />, label: "Выкупы", value: formatQuantity(completedQty), subValue: formatCurrency(completedValue), tooltip: "Успешно выкупленные заказы" },
    { icon: <RotateCcw className="w-4 h-4" />, label: "Возвраты", value: formatQuantity(product.returns), subValue: product.returns > 0 ? `-${formatCurrency(returnsValueNum)}` : formatCurrency(0), tooltip: "Возвращённые товары" },
    { icon: <Percent className="w-4 h-4" />, label: "Процент возврата заказов", value: formatPercent(returnRate), tooltip: "Доля возвращённых заказов от общего числа" },
    { icon: <CreditCard className="w-4 h-4" />, label: "Средний чек", value: formatMoneyNoDecimals(averageCheck), tooltip: "Средняя сумма одного заказа" },
  ];
  const financeMetrics = [
    { icon: <DollarSign className="w-4 h-4" />, label: "Выручка", value: formatCurrency(product.revenue), tooltip: "Выручка со статусом «завершен»" },
    { icon: <TrendingDown className="w-4 h-4" />, label: "Расходы", value: formatCurrency(totalExpenses), tooltip: "Сумма всех расходов из блока Расходы." },
    { icon: <Wallet className="w-4 h-4" />, label: "Прибыль", value: formatCurrency(product.profit), tooltip: "Выручка минус Расходы" },
    { icon: <Target className="w-4 h-4" />, label: "Рентабельность продаж", value: formatPercent(salesProfitability), tooltip: "Прибыль / Выручка" },
    { icon: <BarChart3 className="w-4 h-4" />, label: "Окупаемость инвестиций", value: formatPercent(roi), tooltip: "ROI = Прибыль / Расходы × 100%" },
    { icon: <TrendingUp className="w-4 h-4" />, label: "Тренд выручки", value: formatTrend(revenueTrend), trend: (revenueTrend >= 0 ? "up" : "down") as const, trendValue: "", tooltip: "Сравнение выручки с аналогичным предыдущим периодом (как на Сводке, по данным товара)" },
    { icon: <ArrowDown className="w-4 h-4" />, label: "Упущенная выручка", value: formatCurrency(product.lostRevenue), tooltip: "Потенциальная выручка от товаров без остатков" },
  ];
  const expenseMetrics = [
    { icon: <Percent className="w-4 h-4" />, label: "Комиссия UZUM", value: formatCurrency(product.uzumCommission), tooltip: "Комиссия маркетплейса из отчёта о продажах" },
    { icon: <Truck className="w-4 h-4" />, label: "Логистика UZUM", value: formatCurrency(product.uzumLogistics), tooltip: "Логистический сбор из отчёта о продажах" },
    { icon: <Boxes className="w-4 h-4" />, label: "Себест. прод. тов.", value: formatCurrency(product.cogsTotal), tooltip: "Себестоимость × количество (со статусом завершен)" },
    { icon: <Receipt className="w-4 h-4" />, label: "Налоги", value: formatCurrency(taxAmount), tooltip: `Налог с вкладки Сводка: Выручка × ${taxPercent}%` },
    { icon: <Info className="w-4 h-4" />, label: "Доп. расходы", value: formatCurrency(0), tooltip: "Расходы занесенные во вкладке Доп. расходы." },
  ];
  const warehouseMetrics = [
    { icon: <Warehouse className="w-4 h-4" />, label: "Товаров на складе", value: formatQuantity(product.stock), tooltip: "Общее количество на стороне маркетплейса." },
    { icon: <Tag className="w-4 h-4" />, label: "Себест. тов.", value: formatCurrency(stockCost), tooltip: "Товар на складе × себестоимость." },
    { icon: <ShoppingBag className="w-4 h-4" />, label: "Рознич. цена", value: formatCurrency(stockRetail), tooltip: "Потенциальная сумма к получению за все остатки." },
  ];

  return <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1 text-sm">
        <button onClick={onBack} className="text-primary hover:text-primary/80 transition-colors font-medium">
          Товары
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
            <h2 className="text-lg font-semibold text-foreground">ТОВАР</h2>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center rounded-md px-3 py-1.5 text-sm font-medium bg-green-100 text-green-800 dark:bg-green-950/50 dark:text-green-400">
              Маржинальность: {marginPercentAllTime.toFixed(1)}%
            </span>
            <span className="inline-flex items-center rounded-md px-3 py-1.5 text-sm font-medium bg-violet-100 text-violet-800 dark:bg-violet-950/50 dark:text-violet-400">
              От общей выручки: {revenueSharePercentAllTime.toFixed(1)}%
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Part - Product Details */}
          <div className="space-y-4">
            <div>
              <span className="text-sm text-muted-foreground">Название</span>
              <p className="text-foreground font-medium">{product.name}</p>
            </div>
            <div>
              <span className="text-sm text-muted-foreground">Тип товара</span>
              <p className="text-foreground font-medium">{getProductType()}</p>
            </div>
            <div>
              <span className="text-sm text-muted-foreground">ID товара</span>
              <p className="text-foreground font-medium font-mono">{product.id}</p>
            </div>
            
            {/* Comment Block */}
            <div className="pt-4 border-t border-border">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Комментарий</span>
                </div>
                <span className={`text-xs ${comment.length > 120 ? "text-destructive" : "text-muted-foreground"}`}>
                  {comment.length}/120
                </span>
              </div>
              <Textarea 
                placeholder="Оставьте комментарий к товару..." 
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
                {saveCommentMutation.isPending ? "Сохранение..." : "Сохранить"}
              </Button>
            </div>
          </div>

          {/* Right Part - Variants Table */}
          <div>
            <div className="bg-muted/30 rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th colSpan={3} className="px-3 py-2 text-left text-muted-foreground font-medium">Параметры товара</th>
                    <th className="px-3 py-2 text-center text-muted-foreground font-medium">Заказы</th>
                    <th className="px-3 py-2 text-center text-muted-foreground font-medium">Остатки</th>
                    <th className="px-3 py-2 text-center text-muted-foreground font-medium">Габ. группа</th>
                    <th className="px-3 py-2 text-center text-muted-foreground font-medium">Штрихкод</th>
                    <th className="px-3 py-2 text-center text-muted-foreground font-medium">
                      <div className="flex flex-col items-center">
                        <span>Хранение</span>
                        <span className="text-xs">сут/сум</span>
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
                          <td className="px-3 py-2 text-center">
                            {variant.size_group && variant.size_group !== "-" ? (
                              <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                                variant.size_group === "СГТ" ? "bg-success/20 text-success" : 
                                variant.size_group === "МГТ" ? "bg-warning/20 text-warning" : 
                                "bg-destructive/20 text-destructive"
                              }`}>
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
                      <td colSpan={8} className="px-3 py-4 text-center text-muted-foreground">
                        Нет вариантов товара
                      </td>
                    </tr>
                  )}
                </tbody>
                {productVariants.length > 0 && (
                  <tfoot>
                    <tr className="border-t border-border bg-muted/50">
                      <td colSpan={3} className="px-3 py-2 text-left text-foreground font-medium">Всего</td>
                      <td className="px-3 py-2 text-center text-foreground font-semibold">
                        {formatNumber(productVariants.reduce((sum, v) => sum + v.sales_qty, 0))}
                      </td>
                      <td className="px-3 py-2 text-center text-foreground font-semibold">
                        {formatNumber(productVariants.reduce((sum, v) => sum + (v.stock ?? 0), 0))}
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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryBlock title="ПРОДАЖИ" titleColor="text-chart-4" metrics={salesMetrics} />
        <SummaryBlock title="ФИНАНСЫ" titleColor="text-warning" metrics={financeMetrics} />
        <SummaryBlock title="РАСХОДЫ" titleColor="text-destructive" metrics={expenseMetrics} />
        <SummaryBlock title="СКЛАД" titleColor="text-warning" metrics={warehouseMetrics} />
      </div>

      {/* Продажи по дням — данные по выбранному периоду из фильтра дат */}
      {dateFrom && dateTo ? (
        <div className="mt-6">
          <RevenueDailyChart data={revenueChartData} hideAvgCheck key={`${dateFrom}-${dateTo}`} />
        </div>
      ) : (
        <div className="mt-6 rounded-xl border border-border bg-muted/30 p-6 text-center text-sm text-muted-foreground">
          Выберите период в фильтре дат (справа от фильтра магазинов), чтобы отобразить график «Продажи по дням».
        </div>
      )}
    </div>;
}