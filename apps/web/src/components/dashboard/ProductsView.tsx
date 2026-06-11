import { useState, useMemo, useEffect } from "react";
import {
  Search,
  Layers,
  ChevronUp,
  ChevronDown,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn, getSizeGroupColorClass } from "@/lib/utils";
import { useLanguage } from "@/contexts/LanguageContext";
import { ProductDetailView } from "./ProductDetailView";
import { useQuery } from "@tanstack/react-query";
import { apiGet, buildQueryParams } from "@/lib/api";
import { ProductThumbnail } from "@/components/dashboard/ProductThumbnail";

/** Элемент таблицы товаров: left-out-report_old + sells_report по штрихкоду */
export interface ProductsTableItemType {
  product_id?: string | null;
  product_name: string | null;
  sku: string | null;
  price: number | null;
  sales_qty: number;
  returns_qty: number;
  revenue: number;
  profit: number;
  turnover: number | null;
  stock: number | null;
  size_group: string | null;
  cogs: number;
  cogs_total: number;
  commission: number;
  logistics: number;
  abc_orders: string | null;
  abc_profit: string | null;
  abc_revenue: string | null;
  barcode: string | null;
  product_image_url: string | null;
  storage_cost_per_day: number | null;
  shop: string | null;
}

interface ProductsTableResponse {
  items: ProductsTableItemType[];
}

type SortField =
  | "product_name"
  | "sku"
  | "price"
  | "sales_qty"
  | "returns_qty"
  | "revenue"
  | "profit"
  | "turnover"
  | "stock"
  | "cogs"
  | "commission"
  | "logistics"
  | "abc_orders"
  | "abc_profit"
  | "abc_revenue"
  | "barcode"
  | "size_group"
  | "storage_cost_per_day"
  | "shop";

type SortDirection = "asc" | "desc" | null;

interface ProductsViewProps {
  shop?: string | null;
  /** Пользовательский процент налога (из вкладки Сводка) для карточки товара. */
  taxPercent?: number;
  dateFrom?: string;
  dateTo?: string;
  /** Открыть карточку товара (например, из блока «Ваш бизнес за последние 7 дней»). */
  openProduct?: ProductsTableItemType | null;
  onOpenProductHandled?: () => void;
}

export function ProductsView({
  shop,
  taxPercent = 1,
  dateFrom,
  dateTo,
  openProduct,
  onOpenProductHandled,
}: ProductsViewProps) {
  const { t } = useLanguage();
  const [searchQuery, setSearchQuery] = useState("");
  const [groupByCards, setGroupByCards] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<ProductsTableItemType | null>(null);
  const [sortField, setSortField] = useState<SortField | null>("sales_qty");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  useEffect(() => {
    if (!openProduct) return;
    setSelectedProduct(openProduct);
    onOpenProductHandled?.();
  }, [openProduct, onOpenProductHandled]);

  useEffect(() => {
    if (selectedProduct) {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }, [selectedProduct]);

  const { data: productsData, isLoading: productsLoading } = useQuery({
    queryKey: ["products-table", shop, dateFrom, dateTo],
    queryFn: async () => {
      const params = buildQueryParams({ 
        shop: shop ?? undefined,
        date_from: dateFrom ?? undefined,
        date_to: dateTo ?? undefined,
      });
      return apiGet<ProductsTableResponse>("/api/charts/products-table", params);
    },
    refetchOnWindowFocus: false,
  });

  const products: ProductsTableItemType[] = productsData?.items ?? [];

  // Прибыль и ABC-прибыль в таблице Товары привязываем к введённому проценту налога:
  // Прибыль = сумма revenue_sum по завершённым - сумма (cogs_sum * qty) по завершённым - сумма commission_sum по завершённым - сумма logistics_sum по завершённым - налог с учетом процента на вкладке сводка
  const adjustedProducts: ProductsTableItemType[] = useMemo(() => {
    if (!products.length) return products;
    return products.map((p) => {
      const revenue = p.revenue ?? 0;
      const cogs_total = p.cogs_total ?? 0; // Используем общую себестоимость (сумма cogs_sum * qty по завершённым)
      const commission = p.commission ?? 0;
      const logistics = p.logistics ?? 0;
      const tax = revenue * (taxPercent / 100);
      const profit = revenue - cogs_total - commission - logistics - tax;
      return {
        ...p,
        profit,
      };
    });
  }, [products, taxPercent]);

  // ABC-прибыль: используем значения из бэкенда, рассчитанные за последние 30 дней
  // ABC анализ не пересчитывается на фронтенде, чтобы не зависеть от фильтров date_from/date_to
  const adjustedProductsWithAbc: ProductsTableItemType[] = adjustedProducts;

  // Группировка по карточкам (ID товара из left-out-report_old): одна строка на product_id, метрики суммируются
  const displayProducts: ProductsTableItemType[] = useMemo(() => {
    if (!groupByCards || !adjustedProductsWithAbc.length) return adjustedProductsWithAbc;

    const groupKey = (p: ProductsTableItemType) =>
      (p.product_id || p.sku || p.barcode || "").trim() || `row-${p.barcode}-${p.sku}`;
    const groups = new Map<string, ProductsTableItemType[]>();
    for (const p of adjustedProductsWithAbc) {
      const key = groupKey(p);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push(p);
    }

    const aggregated: ProductsTableItemType[] = [];
    for (const [, rows] of groups) {
      const first = rows[0];
      const same = <T,>(get: (r: ProductsTableItemType) => T) => {
        const v = get(rows[0]);
        return rows.every((r) => get(r) === v) ? v : null;
      };
      const sum = (get: (r: ProductsTableItemType) => number) =>
        rows.reduce((s, r) => s + (get(r) ?? 0), 0);
      // ABC: сравниваем только по штрихкодам, у которых анализ проведён (не null и не пусто); если у всех таких один класс — показываем его
      const sameAbc = (get: (r: ProductsTableItemType) => string | null) => {
        const values = rows.map(get).filter((v): v is string => v != null && String(v).trim() !== "");
        if (values.length === 0) return null;
        const firstVal = values[0];
        return values.every((v) => v === firstVal) ? firstVal : null;
      };

      aggregated.push({
        ...first,
        product_id: first.product_id ?? first.sku ?? first.barcode ?? null,
        product_name: same((r) => r.product_name) ?? "—",
        sku: first.sku,
        price: same((r) => r.price) ?? null,
        sales_qty: sum((r) => r.sales_qty),
        returns_qty: sum((r) => r.returns_qty),
        revenue: sum((r) => r.revenue),
        profit: sum((r) => r.profit),
        turnover: same((r) => r.turnover) ?? null,
        stock: rows.every((r) => r.stock != null) ? sum((r) => r.stock ?? 0) : null,
        size_group: same((r) => r.size_group) ?? null,
        cogs: null, // При группировке по карточкам себестоимость не суммируется, отображается "—"
        cogs_total: sum((r) => r.cogs_total ?? 0), // Суммируем общую себестоимость для расчёта прибыли
        commission: sum((r) => r.commission),
        logistics: sum((r) => r.logistics),
        barcode: rows.length > 1 ? "—" : (first.barcode ?? null),
        product_image_url:
          rows.map((r) => r.product_image_url?.trim()).find((url) => url) ?? null,
        // Для группировки по карточкам показываем сумму хранения по всем вариантам карточки.
        storage_cost_per_day: rows.some((r) => r.storage_cost_per_day != null)
          ? sum((r) => r.storage_cost_per_day ?? 0)
          : null,
        shop: same((r) => r.shop) ?? null,
        abc_orders: sameAbc((r) => r.abc_orders),
        abc_profit: sameAbc((r) => r.abc_profit),
        abc_revenue: sameAbc((r) => r.abc_revenue),
      });
    }

    // ABC при группировке: показываем значение только если у всех штрихкодов с проведённым анализом один класс; штрихкоды без анализа не учитываются.
    return aggregated;
  }, [groupByCards, adjustedProductsWithAbc]);

  const productId = (p: ProductsTableItemType, idx: number) =>
    (groupByCards ? (p.product_id || p.sku) : p.barcode) || p.sku || `row-${idx}`;

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat("ru-RU").format(num);
  };

  /** Числа в колонках без суффикса «сум» */
  const formatValue = (price: number) => new Intl.NumberFormat("ru-RU").format(price);

  const getAbcBadge = (abc: string | null) => {
    if (abc == null || abc === "") return null;
    switch (abc) {
      case "A":
        return <Badge className="bg-success/10 text-success hover:bg-success/20 text-xs px-2">A</Badge>;
      case "B":
        return <Badge className="bg-warning/10 text-warning hover:bg-warning/20 text-xs px-2">B</Badge>;
      case "C":
        return <Badge className="bg-muted text-muted-foreground hover:bg-muted/80 text-xs px-2">C</Badge>;
      default:
        return null;
    }
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      if (sortDirection === "asc") {
        setSortDirection("desc");
      } else if (sortDirection === "desc") {
        setSortField(null);
        setSortDirection(null);
      } else {
        setSortDirection("asc");
      }
    } else {
      setSortField(field);
      setSortDirection("asc");
    }
  };

  const getSortIcon = (field: SortField) => {
    const isActive = sortField === field;
    return (
      <span className="flex flex-col ml-0.5">
        <ChevronUp
          className={cn(
            "h-3 w-3 -mb-1",
            isActive && sortDirection === "asc"
              ? "text-primary"
              : "text-muted-foreground/50"
          )}
        />
        <ChevronDown
          className={cn(
            "h-3 w-3",
            isActive && sortDirection === "desc"
              ? "text-primary"
              : "text-muted-foreground/50"
          )}
        />
      </span>
    );
  };

  const filteredProducts = displayProducts.filter((p) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.trim().toLowerCase();
    return (
      (p.product_name?.toLowerCase().includes(q)) ||
      (p.sku?.toLowerCase().includes(q)) ||
      (p.barcode?.toLowerCase().includes(q))
    );
  });

  const ABC_FIELDS: SortField[] = ["abc_orders", "abc_revenue", "abc_profit"];
  const abcRank = (v: string | null | undefined): number => {
    const s = (v ?? "").toString().trim().toUpperCase();
    if (s === "A") return 1;
    if (s === "B") return 2;
    if (s === "C") return 3;
    return 0; // пусто или неизвестное — в конец
  };

  const sortedProducts = [...filteredProducts].sort((a, b) => {
    if (!sortField || !sortDirection) return 0;

    let aValue: unknown = a[sortField as keyof ProductsTableItemType];
    let bValue: unknown = b[sortField as keyof ProductsTableItemType];

    const pushEmptyToEnd = sortDirection === "asc" ? Infinity : -Infinity;

    if (ABC_FIELDS.includes(sortField)) {
      const aR = abcRank(aValue as string);
      const bR = abcRank(bValue as string);
      if (aR === 0 && bR === 0) return 0;
      if (aR === 0) return 1;
      if (bR === 0) return -1;
      if (sortDirection === "asc") return aR - bR;
      return bR - aR;
    }

    if (aValue === null || aValue === undefined) aValue = pushEmptyToEnd;
    if (bValue === null || bValue === undefined) bValue = pushEmptyToEnd;

    if (typeof aValue === "string" && typeof bValue === "string") {
      return sortDirection === "asc"
        ? aValue.localeCompare(bValue, "ru")
        : bValue.localeCompare(aValue, "ru");
    }

    if (sortDirection === "asc") {
      return (aValue as number) > (bValue as number) ? 1 : -1;
    } else {
      return (aValue as number) < (bValue as number) ? 1 : -1;
    }
  });

  // Map API item to Product shape for ProductDetailView (как на Сводке: те же формулы по ID карточки)
  const productToDetailShape = (p: ProductsTableItemType) => ({
    id: p.product_id || p.barcode || p.sku || "",
    name: p.product_name ?? "",
    article: p.sku ?? "",
    price: p.price ?? 0,
    sales: p.sales_qty,
    returns: p.returns_qty,
    revenue: p.revenue,
    lostRevenue: 0,
    turnover: p.turnover ?? 0,
    stock: p.stock ?? 0,
    endsIn: "—",
    costPrice: p.cogs ?? null,
    cogsTotal: p.cogs_total ?? 0,
    uzumCommission: p.commission ?? 0,
    uzumLogistics: p.logistics ?? 0,
    profit: p.profit ?? 0,
    abcOrders: p.abc_orders ?? "",
    abcProfit: p.abc_profit ?? "",
    abcRevenue: p.abc_revenue ?? "",
    barcode: p.barcode ?? "",
    brand: "",
    category: p.size_group ?? "",
    status: "active",
    product_image_url: p.product_image_url ?? null,
  });

  // Отдельный запрос для карточки товара без фильтрации по магазину
  const { data: allProductsData } = useQuery({
    queryKey: ["products-table-all", dateFrom, dateTo],
    queryFn: async () => {
      const params = buildQueryParams({ 
        date_from: dateFrom ?? undefined,
        date_to: dateTo ?? undefined,
        // Не передаем shop, чтобы получить все данные без фильтрации по магазину
      });
      return apiGet<ProductsTableResponse>("/api/charts/products-table", params);
    },
    enabled: !!selectedProduct, // Запрос выполняется только когда товар выбран
    refetchOnWindowFocus: false,
  });

  const allProducts: ProductsTableItemType[] = allProductsData?.items ?? [];

  // Обработка всех товаров для карточки (без фильтрации по магазину)
  const allAdjustedProducts: ProductsTableItemType[] = useMemo(() => {
    if (!allProducts.length) return allProducts;
    return allProducts.map((p) => {
      const revenue = p.revenue ?? 0;
      const cogs_total = p.cogs_total ?? 0; // Используем общую себестоимость (сумма cogs_sum * qty по завершённым)
      const commission = p.commission ?? 0;
      const logistics = p.logistics ?? 0;
      const tax = revenue * (taxPercent / 100);
      const profit = revenue - cogs_total - commission - logistics - tax;
      return {
        ...p,
        profit,
      };
    });
  }, [allProducts, taxPercent]);

  // ABC-прибыль для всех товаров: используем значения из бэкенда, рассчитанные за последние 30 дней
  // ABC анализ не пересчитывается на фронтенде, чтобы не зависеть от фильтров date_from/date_to
  const allAdjustedProductsWithAbc: ProductsTableItemType[] = allAdjustedProducts;

  // If a product is selected, show the detail view (данные по ID карточки: агрегируем все варианты)
  if (selectedProduct) {
    const productId = selectedProduct.product_id || selectedProduct.sku || selectedProduct.barcode;
    const productVariants = allAdjustedProductsWithAbc.filter(p => {
      const pId = p.product_id || p.sku || p.barcode;
      return pId === productId;
    });
    const sum = (get: (r: ProductsTableItemType) => number) =>
      productVariants.reduce((s, r) => s + (get(r) ?? 0), 0);
    const first = productVariants[0];
    const aggregatedProduct: ProductsTableItemType = first
      ? {
          ...first,
          product_id: first.product_id ?? first.sku ?? first.barcode ?? null,
          product_name: first.product_name,
          sku: first.sku,
          price: first.price,
          sales_qty: sum((r) => r.sales_qty),
          returns_qty: sum((r) => r.returns_qty),
          revenue: sum((r) => r.revenue),
          profit: sum((r) => r.profit),
          cogs_total: sum((r) => r.cogs_total ?? 0),
          commission: sum((r) => r.commission ?? 0),
          logistics: sum((r) => r.logistics ?? 0),
          stock: productVariants.every((r) => r.stock != null)
            ? sum((r) => r.stock ?? 0)
            : null,
          cogs: first.cogs,
          product_image_url:
            productVariants.map((r) => r.product_image_url?.trim()).find((url) => url) ?? null,
        }
      : selectedProduct;
    
    const totalRevenue = allAdjustedProductsWithAbc.reduce((s, p) => s + (p.revenue ?? 0), 0);
    return (
      <ProductDetailView
        product={productToDetailShape(aggregatedProduct)}
        variants={productVariants}
        onBack={() => setSelectedProduct(null)}
        taxPercent={taxPercent}
        dateFrom={dateFrom ?? undefined}
        dateTo={dateTo ?? undefined}
        totalRevenue={totalRevenue}
      />
    );
  }

  const SortableHeader = ({ field, children, className }: { field: SortField; children: React.ReactNode; className?: string }) => (
      <TableHead 
        className={cn(
          "sticky top-0 z-20 cursor-pointer select-none text-muted-foreground px-2 py-1",
          "border-b border-border bg-violet-50/95 dark:bg-violet-950/95 backdrop-blur-sm",
          "hover:bg-violet-100/90 dark:hover:bg-violet-900/50",
          className
        )}
        onClick={() => handleSort(field)}
      >
        <div className="flex items-center justify-center gap-1">
          {children}
          {getSortIcon(field)}
        </div>
      </TableHead>
  );

  return (
    <div className="w-full min-w-0 space-y-4">
      {/* Filters & Settings */}
      <div className="flex flex-col gap-4">
        <div className="flex flex-col md:flex-row md:items-center gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder={t('search.byNameArticle')}
              className="pl-10 bg-background"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <div className="flex-1" />

          <Button
            variant={groupByCards ? "default" : "outline"}
            size="sm"
            className={groupByCards ? "bg-primary hover:bg-primary/90 text-primary-foreground" : ""}
            onClick={() => setGroupByCards((prev) => !prev)}
          >
            <Layers className="w-4 h-4 mr-2" />
            {t('products.groupByCards')}
          </Button>
        </div>

        {groupByCards && (
          <p className="text-sm text-muted-foreground">
            Товары сгруппированы по карточкам. Прочерки означают, что значения отличаются для разных характеристик.
          </p>
        )}
      </div>

      {/* Products Table */}
      {productsLoading ? (
        <div className="rounded-lg border border-border p-8 text-center text-muted-foreground">
          Загрузка товаров…
        </div>
      ) : (
      <div className="data-table animate-fade-in w-full min-w-0 max-w-full rounded-lg border border-border">
        <div
          className={cn(
            "max-h-[min(70vh,42rem)] sm:max-h-[min(75vh,48rem)] lg:max-h-[min(78vh,52rem)]",
            "overflow-auto overscroll-contain",
            "touch-pan-x touch-pan-y [scrollbar-gutter:stable]"
          )}
        >
          <Table
            wrapperClassName="overflow-visible min-w-0"
            className="w-max min-w-full caption-bottom"
          >
            <TableHeader>
              <TableRow className="border-border">
                <SortableHeader
                  field="product_name"
                  className={cn(
                    "sticky left-0 z-40 border-r border-border text-center",
                    "min-w-[min(260px,72vw)] sm:min-w-[300px] md:min-w-[360px] max-w-[min(400px,88vw)] md:max-w-[400px]"
                  )}
                >
                  {t('table.productName')}
                </SortableHeader>
                <SortableHeader field="price" className="text-center min-w-[100px]">
                  {t('table.price')}
                </SortableHeader>
                <SortableHeader field="sales_qty" className="text-center min-w-[80px]">
                  {t('summary.sales.orders')}
                </SortableHeader>
                <SortableHeader field="returns_qty" className="text-center min-w-[80px]">
                  {t('summary.sales.returns')}
                </SortableHeader>
                <SortableHeader field="revenue" className="text-center min-w-[120px]">
                  {t('summary.finance.revenue')}
                </SortableHeader>
                <SortableHeader field="profit" className="text-center min-w-[120px]">
                  {t('summary.finance.profit')}
                </SortableHeader>
                <SortableHeader field="turnover" className="text-center min-w-[100px] whitespace-nowrap">
                  {t('table.turnover')}
                </SortableHeader>
                <SortableHeader field="stock" className="text-center min-w-[80px]">
                  {t('table.stock')}
                </SortableHeader>
                <SortableHeader field="size_group" className="text-center min-w-[100px]">
                  {t('table.sizeGroup')}
                </SortableHeader>
                <SortableHeader field="cogs" className="text-center min-w-[120px]">
                  {t('table.costPrice')}
                </SortableHeader>
                <SortableHeader field="commission" className="text-center min-w-[100px]">
                  {t('summary.expense.commissionUzum')}
                </SortableHeader>
                <SortableHeader field="logistics" className="text-center min-w-[100px]">
                  {t('summary.expense.logisticsUzum')}
                </SortableHeader>
                <SortableHeader field="abc_orders" className="text-center min-w-[80px]">
                  {t('table.abcOrders')}
                </SortableHeader>
                <SortableHeader field="abc_revenue" className="text-center min-w-[80px]">
                  {t('table.abcRevenue')}
                </SortableHeader>
                <SortableHeader field="abc_profit" className="text-center min-w-[80px]">
                  {t('table.abcProfit')}
                </SortableHeader>
                <SortableHeader field="barcode" className="text-center min-w-[130px]">
                  {t('product.barcode')}
                </SortableHeader>
                <SortableHeader field="storage_cost_per_day" className="text-center min-w-[100px]">
                  {t('table.storagePerDay')}
                </SortableHeader>
                <SortableHeader field="shop" className="text-center min-w-[120px]">
                  {t('table.shop')}
                </SortableHeader>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedProducts.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={18} className="text-center text-muted-foreground py-8">
                    {t('table.noDataProducts')}
                  </TableCell>
                </TableRow>
              ) : (
              sortedProducts.map((product, idx) => {
                const id = productId(product, idx);
                return (
                <TableRow
                  key={id}
                  className="cursor-pointer hover:bg-muted/50"
                  onClick={() => setSelectedProduct(product)}
                >
                  <TableCell
                    className={cn(
                      "sticky left-0 z-10 border-r border-border bg-gray-50/95 pl-4 backdrop-blur-sm dark:bg-gray-800/90",
                      "min-w-[min(260px,72vw)] sm:min-w-[300px] md:min-w-[360px] max-w-[min(400px,88vw)] md:max-w-[400px]"
                    )}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <ProductThumbnail
                        imageUrl={product.product_image_url}
                        alt={product.product_name ?? t("product.name")}
                      />
                      <div className="min-w-0 break-words whitespace-normal text-sm">
                        <p className="font-medium text-foreground">{product.product_name ?? "—"}</p>
                        <p className="text-xs text-muted-foreground">
                          {groupByCards ? `ID: ${product.product_id ?? "—"}` : `SKU: ${product.sku ?? ""}`}
                        </p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-center font-medium">
                    {product.price != null ? formatValue(product.price) : "—"}
                  </TableCell>
                  <TableCell className="text-center font-medium">
                    {formatNumber(product.sales_qty)}
                  </TableCell>
                  <TableCell className="text-center text-muted-foreground">
                    {formatNumber(product.returns_qty)}
                  </TableCell>
                  <TableCell className="text-center font-medium">
                    {formatValue(product.revenue)}
                  </TableCell>
                  <TableCell className="text-center font-medium">
                    {formatValue(Math.round(product.profit))}
                  </TableCell>
                  <TableCell className="text-center">
                    {product.turnover != null && product.turnover > 0 ? `${product.turnover}` : "—"}
                  </TableCell>
                  <TableCell className="text-center font-medium">
                    {product.stock != null ? formatNumber(product.stock) : "—"}
                  </TableCell>
                  <TableCell className="text-center">
                    <span className={cn("inline-block px-2 py-0.5 rounded-md text-sm font-medium", getSizeGroupColorClass(product.size_group))}>
                      {product.size_group ?? "—"}
                    </span>
                  </TableCell>
                  <TableCell className="text-center">
                    {product.cogs ? (
                      <span className="font-medium">{formatValue(product.cogs)}</span>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </TableCell>
                  <TableCell className="text-center text-muted-foreground">
                    {formatValue(product.commission)}
                  </TableCell>
                  <TableCell className="text-center text-muted-foreground">
                    {formatValue(product.logistics)}
                  </TableCell>
                  <TableCell className="text-center">
                    {getAbcBadge(product.abc_orders) ?? <span className="text-muted-foreground">—</span>}
                  </TableCell>
                  <TableCell className="text-center">
                    {getAbcBadge(product.abc_revenue) ?? <span className="text-muted-foreground">—</span>}
                  </TableCell>
                  <TableCell className="text-center">
                    {getAbcBadge(product.abc_profit) ?? <span className="text-muted-foreground">—</span>}
                  </TableCell>
                  <TableCell className="text-center text-muted-foreground text-sm font-mono">
                    {product.barcode ?? "—"}
                  </TableCell>
                  <TableCell className="text-center text-muted-foreground">
                    {product.storage_cost_per_day != null ? formatValue(product.storage_cost_per_day) : "—"}
                  </TableCell>
                  <TableCell className="text-center text-muted-foreground text-sm">
                    {product.shop ?? "—"}
                  </TableCell>
                </TableRow>
              );
              }) )}
            </TableBody>
          </Table>
        </div>
      </div>
      )}
    </div>
  );
}
