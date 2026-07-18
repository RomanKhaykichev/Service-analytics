import { useState, useMemo, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search,
  Layers,
  ChevronUp,
  ChevronDown,
  CircleDollarSign,
} from "lucide-react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
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

const PRODUCTS_TABLE_COL_COUNT = 19;
const PRODUCTS_ROW_ESTIMATE_PX = 64;

/** Элемент таблицы товаров: left-out-report_old + sells_report по штрихкоду */
export interface ProductsTableItemType {
  product_id?: string | null;
  product_name: string | null;
  sku: string | null;
  price: number | null;
  sales_qty: number;
  returns_qty: number;
  orders_qty: number;
  orders_value: number;
  processing_qty: number;
  processing_value: number;
  completed_qty: number;
  completed_value: number;
  returns_value: number;
  revenue: number;
  profit: number;
  turnover: number | null;
  stock: number | null;
  fbs_stock: number | null;
  size_group: string | null;
  cogs: number | null;
  stock_unit_cogs?: number | null;
  stock_cogs_line?: number | null;
  cogs_total: number;
  commission: number;
  logistics: number;
  abc_orders: string | null;
  abc_profit: string | null;
  abc_revenue: string | null;
  barcode: string | null;
  product_image_url: string | null;
  rating?: number | null;
  feedback_quantity?: number | null;
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
  | "fbs_stock"
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
  const navigate = useNavigate();
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

  const {
    data: productsData,
    isPending: productsPending,
    isFetching: productsFetching,
    isError: productsError,
    error: productsErrorDetail,
  } = useQuery({
    queryKey: ["products-table", shop, dateFrom, dateTo],
    queryFn: async () => {
      const params = buildQueryParams({ 
        shop: shop ?? undefined,
        date_from: dateFrom ?? undefined,
        date_to: dateTo ?? undefined,
      });
      return apiGet<ProductsTableResponse>("/api/charts/products-table", params, {
        timeoutMs: 120_000,
      });
    },
    refetchOnWindowFocus: false,
  });

  const products: ProductsTableItemType[] = productsData?.items ?? [];
  const productsInitialLoading = productsPending && !productsData;
  const productsRefetching = productsFetching && !!productsData;

  // Прибыль и ABC-прибыль в таблице Товары привязываем к введённому проценту налога:
  // Прибыль = сумма revenue_sum по завершённым - сумма (cogs_sum * qty) по завершённым - сумма commission_sum по завершённым - сумма logistics_sum по завершённым - налог с учетом процента на вкладке сводка
  const adjustedProducts: ProductsTableItemType[] = useMemo(() => {
    if (!products.length) return products;
    return products.map((p) => {
      const revenue = p.revenue ?? 0;
      const cogs_total = p.cogs_total ?? 0; // SUM(cogs_sum × (qty − returns_qty)) по завершённым
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
        orders_qty: sum((r) => r.orders_qty ?? 0),
        orders_value: sum((r) => r.orders_value ?? 0),
        processing_qty: sum((r) => r.processing_qty ?? 0),
        processing_value: sum((r) => r.processing_value ?? 0),
        completed_qty: sum((r) => r.completed_qty ?? 0),
        completed_value: sum((r) => r.completed_value ?? 0),
        returns_value: sum((r) => r.returns_value ?? 0),
        revenue: sum((r) => r.revenue),
        profit: sum((r) => r.profit),
        turnover: same((r) => r.turnover) ?? null,
        stock: rows.every((r) => r.stock != null) ? sum((r) => r.stock ?? 0) : null,
        fbs_stock: rows.every((r) => r.fbs_stock != null) ? sum((r) => r.fbs_stock ?? 0) : null,
        size_group: same((r) => r.size_group) ?? null,
        cogs: null, // При группировке по карточкам себестоимость не суммируется, отображается "—"
        cogs_total: sum((r) => r.cogs_total ?? 0), // Суммируем общую себестоимость для расчёта прибыли
        commission: sum((r) => r.commission),
        logistics: sum((r) => r.logistics),
        barcode: rows.length > 1 ? "—" : (first.barcode ?? null),
        product_image_url:
          rows.map((r) => r.product_image_url?.trim()).find((url) => url) ?? null,
        rating: first.rating ?? null,
        feedback_quantity: first.feedback_quantity ?? null,
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

  const displayCellText = (value: string | null | undefined) =>
    value != null && String(value).trim() !== "" ? value : "—";

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

  const filteredProducts = useMemo(() => {
    if (!searchQuery.trim()) return displayProducts;
    const q = searchQuery.trim().toLowerCase();
    return displayProducts.filter(
      (p) =>
        (p.product_name?.toLowerCase().includes(q)) ||
        (p.sku?.toLowerCase().includes(q)) ||
        (p.barcode?.toLowerCase().includes(q))
    );
  }, [displayProducts, searchQuery]);

  const abcRank = (v: string | null | undefined): number => {
    const s = (v ?? "").toString().trim().toUpperCase();
    if (s === "A") return 1;
    if (s === "B") return 2;
    if (s === "C") return 3;
    return 0; // пусто или неизвестное — в конец
  };

  const sortedProducts = useMemo(() => {
    if (!sortField || !sortDirection) return filteredProducts;

    const pushEmptyToEnd = sortDirection === "asc" ? Infinity : -Infinity;
    const abcFields: SortField[] = ["abc_orders", "abc_revenue", "abc_profit"];

    return [...filteredProducts].sort((a, b) => {
      let aValue: unknown = a[sortField as keyof ProductsTableItemType];
      let bValue: unknown = b[sortField as keyof ProductsTableItemType];

      if (abcFields.includes(sortField)) {
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
      }
      return (aValue as number) < (bValue as number) ? 1 : -1;
    });
  }, [filteredProducts, sortField, sortDirection]);

  const tableScrollRef = useRef<HTMLDivElement>(null);
  const rowVirtualizer = useVirtualizer({
    count: sortedProducts.length,
    getScrollElement: () => tableScrollRef.current,
    estimateSize: () => PRODUCTS_ROW_ESTIMATE_PX,
    overscan: 12,
  });
  const virtualRows = rowVirtualizer.getVirtualItems();
  const paddingTop = virtualRows.length > 0 ? virtualRows[0].start : 0;
  const paddingBottom =
    virtualRows.length > 0
      ? rowVirtualizer.getTotalSize() - virtualRows[virtualRows.length - 1].end
      : 0;

  // Map API item to Product shape for ProductDetailView (как на Сводке: те же формулы по ID карточки)
  const productToDetailShape = (p: ProductsTableItemType) => ({
    id: p.product_id || p.barcode || p.sku || "",
    name: p.product_name ?? "",
    article: p.sku ?? "",
    price: p.price ?? 0,
    sales: p.orders_qty ?? p.sales_qty,
    returns: p.returns_qty,
    ordersValue: p.orders_value ?? 0,
    processingQty: p.processing_qty ?? 0,
    processingValue: p.processing_value ?? 0,
    completedQty: p.completed_qty ?? 0,
    completedValue: p.completed_value ?? 0,
    returnsValue: p.returns_value ?? 0,
    revenue: p.revenue,
    lostRevenue: 0,
    turnover: p.turnover ?? 0,
    stock: p.stock ?? 0,
    fbsStock: p.fbs_stock ?? 0,
    endsIn: "—",
    costPrice: p.cogs ?? null,
    stockUnitCogs: p.stock_unit_cogs ?? null,
    stockCogsLine: p.stock_cogs_line ?? null,
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
    rating: p.rating ?? null,
    feedback_quantity: p.feedback_quantity ?? null,
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
      return apiGet<ProductsTableResponse>("/api/charts/products-table", params, {
        timeoutMs: 120_000,
      });
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
      const cogs_total = p.cogs_total ?? 0; // SUM(cogs_sum × (qty − returns_qty)) по завершённым
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
          orders_qty: sum((r) => r.orders_qty ?? 0),
          orders_value: sum((r) => r.orders_value ?? 0),
          processing_qty: sum((r) => r.processing_qty ?? 0),
          processing_value: sum((r) => r.processing_value ?? 0),
          completed_qty: sum((r) => r.completed_qty ?? 0),
          completed_value: sum((r) => r.completed_value ?? 0),
          returns_value: sum((r) => r.returns_value ?? 0),
          revenue: sum((r) => r.revenue),
          profit: sum((r) => r.profit),
          cogs_total: sum((r) => r.cogs_total ?? 0),
          commission: sum((r) => r.commission ?? 0),
          logistics: sum((r) => r.logistics ?? 0),
          stock: productVariants.every((r) => r.stock != null)
            ? sum((r) => r.stock ?? 0)
            : null,
          fbs_stock: productVariants.every((r) => r.fbs_stock != null)
            ? sum((r) => r.fbs_stock ?? 0)
            : null,
          cogs: first.cogs,
          stock_unit_cogs: first.stock_unit_cogs,
          stock_cogs_line: sum((r) => r.stock_cogs_line ?? 0),
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

          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                navigate(
                  shop
                    ? `/cogs?shop=${encodeURIComponent(shop)}`
                    : "/cogs",
                )
              }
            >
              <CircleDollarSign className="w-4 h-4 mr-2" />
              {t('products.enterCogs')}
            </Button>
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
        </div>

        {groupByCards && (
          <p className="text-sm text-muted-foreground">
            Товары сгруппированы по карточкам. Прочерки означают, что значения отличаются для разных характеристик.
          </p>
        )}
      </div>

      {/* Products Table */}
      {productsInitialLoading ? (
        <div className="rounded-lg border border-border p-8 text-center text-muted-foreground">
          {t('products.loading')}
        </div>
      ) : productsError ? (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-8 text-center text-destructive">
          {productsErrorDetail instanceof Error
            ? productsErrorDetail.message
            : t('products.loadError')}
        </div>
      ) : (
      <div className="relative data-table animate-fade-in w-full min-w-0 max-w-full rounded-lg border border-border">
        {productsRefetching ? (
          <div className="absolute inset-0 z-50 flex items-center justify-center rounded-lg bg-background/60 backdrop-blur-[1px]">
            <span className="text-sm text-muted-foreground">{t('products.updating')}</span>
          </div>
        ) : null}
        <div
          ref={tableScrollRef}
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
                <SortableHeader field="stock" className="text-center min-w-[80px] whitespace-nowrap">
                  {t('table.stockFbo')}
                </SortableHeader>
                <SortableHeader field="fbs_stock" className="text-center min-w-[80px] whitespace-nowrap">
                  {t('table.stockFbs')}
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
                  <TableCell colSpan={PRODUCTS_TABLE_COL_COUNT} className="text-center text-muted-foreground py-8">
                    {t('table.noDataProducts')}
                  </TableCell>
                </TableRow>
              ) : (
                <>
                  {paddingTop > 0 ? (
                    <tr aria-hidden="true">
                      <td
                        colSpan={PRODUCTS_TABLE_COL_COUNT}
                        style={{ height: paddingTop, padding: 0, border: 0 }}
                      />
                    </tr>
                  ) : null}
                  {virtualRows.map((virtualRow) => {
                    const product = sortedProducts[virtualRow.index];
                    const id = productId(product, virtualRow.index);
                    return (
                <TableRow
                  key={id}
                  data-index={virtualRow.index}
                  ref={rowVirtualizer.measureElement}
                  className="cursor-pointer hover:bg-muted/50"
                  onClick={() => setSelectedProduct(product)}
                >
                  <TableCell
                    className={cn(
                      "sticky left-0 z-10 border-r border-border bg-gray-50/95 pl-4 dark:bg-gray-800/90",
                      "min-w-[min(260px,72vw)] sm:min-w-[300px] md:min-w-[360px] max-w-[min(400px,88vw)] md:max-w-[400px]"
                    )}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <ProductThumbnail
                        imageUrl={product.product_image_url}
                        alt={product.product_name ?? t("product.name")}
                      />
                      <div className="min-w-0 break-words whitespace-normal text-sm">
                        <p className="font-medium text-foreground">{displayCellText(product.product_name)}</p>
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
                  <TableCell className="text-center font-medium">
                    {product.fbs_stock != null ? formatNumber(product.fbs_stock) : "—"}
                  </TableCell>
                  <TableCell className="text-center">
                    <span className={cn("inline-block px-2 py-0.5 rounded-md text-sm font-medium", getSizeGroupColorClass(product.size_group))}>
                      {product.size_group ?? "—"}
                    </span>
                  </TableCell>
                  <TableCell className="text-center">
                    {product.cogs != null ? (
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
                  })}
                  {paddingBottom > 0 ? (
                    <tr aria-hidden="true">
                      <td
                        colSpan={PRODUCTS_TABLE_COL_COUNT}
                        style={{ height: paddingBottom, padding: 0, border: 0 }}
                      />
                    </tr>
                  ) : null}
                </>
              )}
            </TableBody>
          </Table>
        </div>
      </div>
      )}
    </div>
  );
}
