import { ChevronRight, Package as PackageIcon, Palette, Ruler, Barcode, MessageSquare } from "lucide-react";
import { useState } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { ShoppingCart, Truck, Package, RotateCcw, Percent, CreditCard, DollarSign, TrendingDown, Wallet, Target, BarChart3, TrendingUp, ArrowDown, Receipt, AlertTriangle, Boxes, Warehouse, Tag, ShoppingBag } from "lucide-react";
import { SummaryBlock } from "./SummaryBlock";
import { RevenueDailyChart } from "./RevenueDailyChart";
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
  uzumCommission: number;
  uzumLogistics: number;
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
  }>;
  onBack: () => void;
  /** Пользовательский процент налога (из вкладки Сводка). По умолчанию 1. */
  taxPercent?: number;
}
export function ProductDetailView({
  product,
  variants = [],
  onBack,
  taxPercent = 1,
}: ProductDetailViewProps) {
  const [comment, setComment] = useState("");
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
  const salesMetrics = [{
    icon: <ShoppingCart className="w-4 h-4" />,
    label: "Заказы",
    value: `${product.sales} шт`,
    subValue: formatPrice(product.revenue),
    tooltip: "Общее количество заказов и их сумма"
  }, {
    icon: <Truck className="w-4 h-4" />,
    label: "Доставляются",
    value: `${Math.floor(product.sales * 0.12)} шт`,
    subValue: formatPrice(Math.floor(product.revenue * 0.12)),
    tooltip: "Заказы в процессе доставки"
  }, {
    icon: <Package className="w-4 h-4" />,
    label: "Выкупы",
    value: `${product.sales - product.returns} шт`,
    subValue: formatPrice(product.revenue - product.lostRevenue),
    tooltip: "Успешно выкупленные заказы"
  }, {
    icon: <RotateCcw className="w-4 h-4" />,
    label: "Возвраты",
    value: `${product.returns} шт`,
    subValue: `-${formatPrice(Math.floor(product.returns * product.price))}`,
    tooltip: "Возвращённые товары"
  }, {
    icon: <Percent className="w-4 h-4" />,
    label: "Процент выкупа заказов",
    value: `${((product.sales - product.returns) / product.sales * 100).toFixed(1)}%`,
    tooltip: "Доля выкупленных заказов от общего числа"
  }, {
    icon: <CreditCard className="w-4 h-4" />,
    label: "Средний чек",
    value: formatPrice(product.price),
    tooltip: "Средняя сумма одного заказа"
  }];
  const financeMetrics = [{
    icon: <DollarSign className="w-4 h-4" />,
    label: "Выручка",
    value: formatPrice(product.revenue),
    tooltip: "Общая выручка за период"
  }, {
    icon: <TrendingDown className="w-4 h-4" />,
    label: "Расходы",
    value: formatPrice(product.uzumCommission * product.sales + product.uzumLogistics * product.sales),
    tooltip: "Общие расходы за период"
  }, {
    icon: <Wallet className="w-4 h-4" />,
    label: "Прибыль",
    value: formatPrice(product.revenue - (product.uzumCommission + product.uzumLogistics) * product.sales),
    tooltip: "Чистая прибыль после всех расходов"
  }, {
    icon: <Target className="w-4 h-4" />,
    label: "Рентабельность продаж",
    value: `${((product.revenue - (product.uzumCommission + product.uzumLogistics) * product.sales) / product.revenue * 100).toFixed(1)}%`,
    tooltip: "Отношение прибыли к выручке"
  }, {
    icon: <BarChart3 className="w-4 h-4" />,
    label: "Окупаемость инвестиций",
    value: `${(product.turnover * 10).toFixed(1)}%`,
    tooltip: "ROI - возврат инвестиций"
  }, {
    icon: <TrendingUp className="w-4 h-4" />,
    label: "Тренд выручки",
    value: "-12%",
    trend: "down" as const,
    trendValue: "",
    tooltip: "Изменение выручки относительно прошлого периода"
  }, {
    icon: <ArrowDown className="w-4 h-4" />,
    label: "Упущенная выручка",
    value: formatPrice(product.lostRevenue),
    tooltip: "Потенциальная выручка от отменённых заказов"
  }];
  const expenseMetrics = [{
    icon: <Percent className="w-4 h-4" />,
    label: "Комиссия UZUM",
    value: formatPrice(product.uzumCommission * product.sales),
    tooltip: "Комиссия маркетплейса"
  }, {
    icon: <Truck className="w-4 h-4" />,
    label: "Логистика UZUM",
    value: formatPrice(product.uzumLogistics * product.sales),
    tooltip: "Расходы на логистику"
  }, {
    icon: <Target className="w-4 h-4" />,
    label: "Реклама UZUM",
    value: formatPrice(Math.floor(product.revenue * 0.02)),
    tooltip: "Расходы на рекламу"
  }, {
    icon: <AlertTriangle className="w-4 h-4" />,
    label: "Штрафы UZUM",
    value: "0 сум",
    tooltip: "Штрафы от маркетплейса"
  }, {
    icon: <Boxes className="w-4 h-4" />,
    label: "Себест. проданных товаров",
    value: product.costPrice ? formatPrice(product.costPrice * product.sales) : "—",
    tooltip: "Себестоимость проданных товаров"
  }, {
    icon: <Receipt className="w-4 h-4" />,
    label: "Налог",
    value: formatPrice(Math.floor(product.revenue * (taxPercent / 100))),
    tooltip: `Налог = Выручка × ${taxPercent}%`
  }];
  const warehouseMetrics = [{
    icon: <Warehouse className="w-4 h-4" />,
    label: "Товаров на складах",
    value: `${product.stock} шт`,
    tooltip: "Общее количество товаров на складе"
  }, {
    icon: <Tag className="w-4 h-4" />,
    label: "Себест. товара на складе",
    value: product.costPrice ? formatPrice(product.costPrice * product.stock) : "—",
    tooltip: "Общая себестоимость запасов"
  }, {
    icon: <ShoppingBag className="w-4 h-4" />,
    label: "Розничная цена товаров",
    value: formatPrice(product.price * product.stock),
    tooltip: "Общая розничная стоимость запасов"
  }];

  // Chart metrics for the revenue daily chart
  const chartMetrics = {
    averageCheck: formatPrice(product.price),
    orders: product.sales,
    revenue: formatPrice(product.revenue),
    stockItems: product.stock
  };
  return <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1 text-sm">
        <button onClick={onBack} className="text-primary hover:text-primary/80 transition-colors font-medium">
          Мои продажи на UZUM
        </button>
        <ChevronRight className="w-4 h-4 text-muted-foreground" />
        <button onClick={onBack} className="text-muted-foreground hover:text-foreground transition-colors">
          Товары
        </button>
        <ChevronRight className="w-4 h-4 text-muted-foreground" />
        <span className="text-foreground font-medium truncate max-w-[300px]">
          {product.name}
        </span>
      </nav>

      {/* Product Info Block */}
      <div className="bg-card border border-border rounded-lg p-6">
        <div className="flex items-center gap-2 mb-4">
          <PackageIcon className="w-5 h-5 text-primary" />
          <h2 className="text-lg font-semibold text-foreground">ТОВАР</h2>
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
              <div className="flex items-center gap-2 mb-2">
                <MessageSquare className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Комментарий</span>
              </div>
              <Textarea placeholder="Оставьте комментарий к товару..." value={comment} onChange={e => setComment(e.target.value)} className="min-h-[80px] resize-none" />
              <Button size="sm" className="mt-2" disabled={!comment.trim()}>
                Сохранить
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

      {/* Revenue Chart with Metrics */}
      <div className="bg-card border border-border rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-foreground">Выручка по дням</h3>
          <div className="flex items-center gap-6 text-sm">
            <div className="flex flex-col items-center">
              
              
            </div>
            <div className="flex flex-col items-center">
              
              
            </div>
            <div className="flex flex-col items-center">
              
              
            </div>
            <div className="flex flex-col items-center">
              
              
            </div>
          </div>
        </div>
        <RevenueDailyChart productName={product.name} showCommentButton={true} />
      </div>
    </div>;
}