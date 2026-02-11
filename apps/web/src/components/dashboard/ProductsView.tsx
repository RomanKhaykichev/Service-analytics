import { useState, useMemo } from "react";
import {
  Search,
  Download,
  Layers,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
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
import { cn } from "@/lib/utils";
import { ProductDetailView } from "./ProductDetailView";
import { toast } from "sonner";
import * as XLSX from "xlsx";
import { useQuery } from "@tanstack/react-query";
import { apiGet, buildQueryParams } from "@/lib/api";

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
  commission: number;
  logistics: number;
  abc_orders: string | null;
  abc_profit: string | null;
  abc_revenue: string | null;
  barcode: string | null;
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
}

export function ProductsView({ shop, taxPercent = 1, dateFrom, dateTo }: ProductsViewProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [groupByCards, setGroupByCards] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<ProductsTableItemType | null>(null);
  const [sortField, setSortField] = useState<SortField | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);

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
  // Прибыль = Выручка - Себестоимость - Комиссия - Логистика - (Выручка × Налог%).
  const adjustedProducts: ProductsTableItemType[] = useMemo(() => {
    if (!products.length) return products;
    return products.map((p) => {
      const revenue = p.revenue ?? 0;
      const cogs = p.cogs ?? 0;
      const commission = p.commission ?? 0;
      const logistics = p.logistics ?? 0;
      const tax = revenue * (taxPercent / 100);
      const profit = revenue - cogs - commission - logistics - tax;
      return {
        ...p,
        profit,
      };
    });
  }, [products, taxPercent]);

  // ABC-прибыль: классификация A/B/C по скорректированной прибыли
  const adjustedProductsWithAbc: ProductsTableItemType[] = useMemo(() => {
    if (!adjustedProducts.length) return adjustedProducts;

    // Готовим список (ключ, прибыль) для ABC-классификации
    const itemsForAbc = adjustedProducts
      .map((p) => {
        const key = (p.barcode || p.sku || "").trim();
        return key ? { key, profit: p.profit } : null;
      })
      .filter((x): x is { key: string; profit: number } => x !== null);

    const totalProfit = itemsForAbc.reduce(
      (sum, item) => sum + Math.max(item.profit, 0),
      0
    );

    const abcMap = new Map<string, string>();
    if (totalProfit > 0) {
      const sorted = [...itemsForAbc].sort((a, b) => b.profit - a.profit);
      let cumulative = 0;
      for (const item of sorted) {
        const profitPos = Math.max(item.profit, 0);
        if (profitPos <= 0) {
          abcMap.set(item.key, "C");
          continue;
        }
        cumulative += profitPos;
        const share = (cumulative / totalProfit) * 100;
        if (share <= 80) {
          abcMap.set(item.key, "A");
        } else if (share <= 95) {
          abcMap.set(item.key, "B");
        } else {
          abcMap.set(item.key, "C");
        }
      }
    }

    return adjustedProducts.map((p) => {
      const key = (p.barcode || p.sku || "").trim();
      const abcProfit = key ? abcMap.get(key) ?? p.abc_profit : p.abc_profit;
      return {
        ...p,
        abc_profit: abcProfit,
      };
    });
  }, [adjustedProducts]);

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
      const same = <T>(get: (r: ProductsTableItemType) => T) => {
        const v = get(rows[0]);
        return rows.every((r) => get(r) === v) ? v : null;
      };
      const sum = (get: (r: ProductsTableItemType) => number) =>
        rows.reduce((s, r) => s + (get(r) ?? 0), 0);

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
        commission: sum((r) => r.commission),
        logistics: sum((r) => r.logistics),
        barcode: rows.length > 1 ? "—" : (first.barcode ?? null),
        storage_cost_per_day: same((r) => r.storage_cost_per_day) ?? null,
        shop: same((r) => r.shop) ?? null,
        abc_orders: null,
        abc_profit: null,
        abc_revenue: null,
      });
    }

    // Пересчёт ABC по сгруппированным метрикам
    const totalOrders = aggregated.reduce((s, p) => s + Math.max(p.sales_qty, 0), 0);
    const totalProfit = aggregated.reduce((s, p) => s + Math.max(p.profit, 0), 0);
    const totalRevenue = aggregated.reduce((s, p) => s + Math.max(p.revenue, 0), 0);

    const byOrders = [...aggregated].sort((a, b) => b.sales_qty - a.sales_qty);
    let cum = 0;
    const abcOrders: string[] = [];
    byOrders.forEach((row, i) => {
      cum += Math.max(row.sales_qty, 0);
      const share = totalOrders > 0 ? (cum / totalOrders) * 100 : 0;
      abcOrders[i] = share <= 80 ? "A" : share <= 95 ? "B" : "C";
    });

    const byProfit = [...aggregated].sort((a, b) => b.profit - a.profit);
    cum = 0;
    const abcProfit: string[] = [];
    byProfit.forEach((row, i) => {
      cum += Math.max(row.profit, 0);
      const share = totalProfit > 0 ? (cum / totalProfit) * 100 : 0;
      abcProfit[i] = share <= 80 ? "A" : share <= 95 ? "B" : "C";
    });

    const byRevenue = [...aggregated].sort((a, b) => b.revenue - a.revenue);
    cum = 0;
    const abcRevenue: string[] = [];
    byRevenue.forEach((row, i) => {
      cum += Math.max(row.revenue, 0);
      const share = totalRevenue > 0 ? (cum / totalRevenue) * 100 : 0;
      abcRevenue[i] = share <= 80 ? "A" : share <= 95 ? "B" : "C";
    });

    const orderIndex = new Map(byOrders.map((r, i) => [groupKey(r), i]));
    const profitIndex = new Map(byProfit.map((r, i) => [groupKey(r), i]));
    const revenueIndex = new Map(byRevenue.map((r, i) => [groupKey(r), i]));

    return aggregated.map((p) => {
      const key = groupKey(p);
      return {
        ...p,
        abc_orders: orderIndex.get(key) != null ? abcOrders[orderIndex.get(key)!] : null,
        abc_profit: profitIndex.get(key) != null ? abcProfit[profitIndex.get(key)!] : null,
        abc_revenue: revenueIndex.get(key) != null ? abcRevenue[revenueIndex.get(key)!] : null,
      };
    });
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
    if (sortField !== field) {
      return <ArrowUpDown className="w-3 h-3 ml-1 opacity-50" />;
    }
    if (sortDirection === "asc") {
      return <ArrowUp className="w-3 h-3 ml-1" />;
    }
    if (sortDirection === "desc") {
      return <ArrowDown className="w-3 h-3 ml-1" />;
    }
    return <ArrowUpDown className="w-3 h-3 ml-1 opacity-50" />;
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

  const sortedProducts = [...filteredProducts].sort((a, b) => {
    if (!sortField || !sortDirection) return 0;

    let aValue: unknown = a[sortField as keyof ProductsTableItemType];
    let bValue: unknown = b[sortField as keyof ProductsTableItemType];

    if (aValue === null || aValue === undefined) aValue = sortDirection === "asc" ? Infinity : -Infinity;
    if (bValue === null || bValue === undefined) bValue = sortDirection === "asc" ? Infinity : -Infinity;

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

  const handleExportXLSX = () => {
    const selectedData = sortedProducts.map((p) => ({
        "Наименование": p.product_name ?? "",
        "Артикул": p.sku ?? "",
        "Цена": p.price ?? "",
        "Заказы": p.sales_qty,
        "Возвраты": p.returns_qty,
        "Выручка": p.revenue,
        "Прибыль": p.profit,
        "Оборачиваемость": p.turnover ?? "",
        "Остаток": p.stock ?? "",
        "Габаритная группа": p.size_group ?? "-",
        "Себестоимость": p.cogs || "",
        "Комиссия": p.commission,
        "Логистика": p.logistics,
        "ABC заказы": p.abc_orders ?? "",
        "ABC прибыль": p.abc_profit ?? "",
        "ABC выручка": p.abc_revenue ?? "",
        "Штрихкод": p.barcode ?? "",
        "Хранение сут/сум": p.storage_cost_per_day ?? "",
        "Магазин": p.shop ?? "",
      }));

    const worksheet = XLSX.utils.json_to_sheet(selectedData);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Товары");
    XLSX.writeFile(workbook, `товары_${new Date().toISOString().split("T")[0]}.xlsx`);
    toast.success(`Выгружено ${selectedData.length} товаров`);
  };

  // Map API item to Product shape for ProductDetailView
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
    costPrice: p.cogs || null,
    uzumCommission: p.commission,
    uzumLogistics: p.logistics,
    abcOrders: p.abc_orders ?? "",
    abcProfit: p.abc_profit ?? "",
    abcRevenue: p.abc_revenue ?? "",
    barcode: p.barcode ?? "",
    brand: "",
    category: p.size_group ?? "",
    status: "active",
  });

  // If a product is selected, show the detail view
  if (selectedProduct) {
    // Находим все товары с тем же product_id (принадлежат к ID карточки)
    // Используем исходные данные без группировки (adjustedProductsWithAbc), чтобы каждый товар отображался отдельной строкой по штрихкоду
    const productId = selectedProduct.product_id || selectedProduct.sku || selectedProduct.barcode;
    const productVariants = adjustedProductsWithAbc.filter(p => {
      const pId = p.product_id || p.sku || p.barcode;
      return pId === productId;
    });
    
    return (
      <ProductDetailView
        product={productToDetailShape(selectedProduct)}
        variants={productVariants}
        onBack={() => setSelectedProduct(null)}
        taxPercent={taxPercent}
      />
    );
  }

  const SortableHeader = ({ field, children, className }: { field: SortField; children: React.ReactNode; className?: string }) => (
    <TableHead 
      className={cn("cursor-pointer hover:bg-muted/50 select-none", className)}
      onClick={() => handleSort(field)}
    >
      <div className="flex items-center gap-1">
        {children}
        {getSortIcon(field)}
      </div>
    </TableHead>
  );

  return (
    <div className="space-y-4">
      {/* Filters & Settings */}
      <div className="flex flex-col gap-4">
        <div className="flex flex-col md:flex-row md:items-center gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Поиск по названию, артикулу..."
              className="pl-10 bg-background"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <div className="flex-1" />

          <Button 
            variant="outline" 
            size="sm"
            onClick={handleExportXLSX}
            disabled={sortedProducts.length === 0}
          >
            <Download className="w-4 h-4 mr-2" />
            Выгрузить в XLSX
          </Button>

          <Button
            variant={groupByCards ? "default" : "outline"}
            size="sm"
            className={groupByCards ? "bg-primary hover:bg-primary/90 text-primary-foreground" : ""}
            onClick={() => setGroupByCards((prev) => !prev)}
          >
            <Layers className="w-4 h-4 mr-2" />
            Сгруппировать по карточкам
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
      <div className="data-table animate-fade-in rounded-lg border border-border">
        <div className="overflow-x-auto overflow-y-visible">
          <Table className="min-w-[1600px]">
            <TableHeader>
              <TableRow className="hover:bg-transparent bg-muted/50">
                <SortableHeader field="product_name" className="min-w-[400px] max-w-[400px] sticky left-0 bg-muted z-10 border-r-0">
                  Наименование
                </SortableHeader>
                <SortableHeader field="price" className="text-center min-w-[100px]">
                  Цена
                </SortableHeader>
                <SortableHeader field="sales_qty" className="text-center min-w-[80px]">
                  Заказы
                </SortableHeader>
                <SortableHeader field="returns_qty" className="text-center min-w-[80px]">
                  Возвраты
                </SortableHeader>
                <SortableHeader field="revenue" className="text-center min-w-[120px]">
                  Выручка
                </SortableHeader>
                <SortableHeader field="profit" className="text-center min-w-[120px]">
                  Прибыль
                </SortableHeader>
                <SortableHeader field="turnover" className="text-center min-w-[100px] whitespace-nowrap">
                  Оборач-ть
                </SortableHeader>
                <SortableHeader field="stock" className="text-center min-w-[80px]">
                  Остаток
                </SortableHeader>
                <SortableHeader field="size_group" className="text-center min-w-[100px]">
                  Габаритная группа
                </SortableHeader>
                <SortableHeader field="cogs" className="text-center min-w-[120px]">
                  Себестоимость
                </SortableHeader>
                <SortableHeader field="commission" className="text-center min-w-[100px]">
                  Комиссия
                </SortableHeader>
                <SortableHeader field="logistics" className="text-center min-w-[100px]">
                  Логистика
                </SortableHeader>
                <SortableHeader field="abc_orders" className="text-center min-w-[80px]">
                  ABC заказы
                </SortableHeader>
                <SortableHeader field="abc_profit" className="text-center min-w-[80px]">
                  ABC прибыль
                </SortableHeader>
                <SortableHeader field="abc_revenue" className="text-center min-w-[80px]">
                  ABC выручка
                </SortableHeader>
                <SortableHeader field="barcode" className="text-center min-w-[130px]">
                  Штрихкод
                </SortableHeader>
                <SortableHeader field="storage_cost_per_day" className="text-center min-w-[100px]">
                  Хранение сут/сум
                </SortableHeader>
                <SortableHeader field="shop" className="text-center min-w-[120px]">
                  Магазин
                </SortableHeader>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedProducts.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={18} className="text-center text-muted-foreground py-8">
                    Нет данных. Загрузите left-out-report_old и sells_report.
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
                  <TableCell className="sticky left-0 bg-card z-10 min-w-[400px] max-w-[400px] border-r-0">
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="w-3 h-3 rounded-full border-2 border-purple-500 bg-transparent shrink-0" aria-hidden />
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
                    {formatValue(product.profit)}
                  </TableCell>
                  <TableCell className="text-center">
                    {product.turnover != null && product.turnover > 0 ? `${product.turnover}` : "—"}
                  </TableCell>
                  <TableCell className="text-center font-medium">
                    {product.stock != null ? formatNumber(product.stock) : "—"}
                  </TableCell>
                  <TableCell className="text-center">
                    {(() => {
                      const sg = (product.size_group ?? "").trim().toUpperCase();
                      const isSGT = sg === "СГТ";
                      const isMGT = sg === "МГТ";
                      const isBGT = sg === "БГТ";
                      const bgClass = isSGT
                        ? "bg-green-100 text-green-800"
                        : isMGT
                          ? "bg-orange-100 text-orange-800"
                          : isBGT
                            ? "bg-red-100 text-red-800"
                            : "bg-muted/60 text-muted-foreground";
                      return (
                        <span className={`inline-block px-2 py-0.5 rounded-md text-sm font-medium ${bgClass}`}>
                          {product.size_group ?? "—"}
                        </span>
                      );
                    })()}
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
                    {getAbcBadge(product.abc_orders)}
                  </TableCell>
                  <TableCell className="text-center">
                    {getAbcBadge(product.abc_profit)}
                  </TableCell>
                  <TableCell className="text-center">
                    {getAbcBadge(product.abc_revenue)}
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
