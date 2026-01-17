import { useState } from "react";
import {
  Search,
  Download,
  MoreHorizontal,
  Eye,
  Edit,
  Trash2,
  Settings,
  Layers,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import { ProductDetailView } from "./ProductDetailView";
import { toast } from "sonner";
import * as XLSX from "xlsx";

type AvailabilityStatus = "excess" | "out_of_stock" | "needs_supply";

const products = [
  {
    id: "SKU-001",
    name: "UZUM Smart Kettle Pro",
    article: "KTL-PRO-001",
    price: 189000,
    sales: 1245,
    returns: 23,
    revenue: 235305000,
    lostRevenue: 4536000,
    turnover: 12.5,
    stock: 342,
    endsIn: "45 дней",
    costPrice: null as number | null,
    uzumCommission: 18900,
    uzumLogistics: 12000,
    abcOrders: "A",
    abcProfit: "A",
    abcRevenue: "A",
    barcode: "4780012345001",
    brand: "UZUM Home",
    category: "Электроника",
    status: "active",
    availability: "excess" as AvailabilityStatus,
  },
  {
    id: "SKU-002",
    name: "UZUM Wireless Earbuds X5",
    article: "EAR-X5-002",
    price: 245000,
    sales: 987,
    returns: 15,
    revenue: 241815000,
    lostRevenue: 2450000,
    turnover: 8.3,
    stock: 156,
    endsIn: "21 день",
    costPrice: 120000,
    uzumCommission: 24500,
    uzumLogistics: 8000,
    abcOrders: "A",
    abcProfit: "B",
    abcRevenue: "A",
    barcode: "4780012345002",
    brand: "UZUM Tech",
    category: "Электроника",
    status: "active",
    availability: "needs_supply" as AvailabilityStatus,
  },
  {
    id: "SKU-003",
    name: "UZUM Fitness Band Plus",
    article: "FIT-PLUS-003",
    price: 156000,
    sales: 876,
    returns: 8,
    revenue: 136656000,
    lostRevenue: 1560000,
    turnover: 15.2,
    stock: 89,
    endsIn: "12 дней",
    costPrice: 75000,
    uzumCommission: 15600,
    uzumLogistics: 6000,
    abcOrders: "B",
    abcProfit: "A",
    abcRevenue: "B",
    barcode: "4780012345003",
    brand: "UZUM Fit",
    category: "Электроника",
    status: "low_stock",
    availability: "needs_supply" as AvailabilityStatus,
  },
  {
    id: "SKU-004",
    name: "Кухонный комбайн UZUM",
    article: "KMB-UZ-004",
    price: 425000,
    sales: 543,
    returns: 12,
    revenue: 230775000,
    lostRevenue: 8500000,
    turnover: 6.8,
    stock: 234,
    endsIn: "56 дней",
    costPrice: null,
    uzumCommission: 42500,
    uzumLogistics: 25000,
    abcOrders: "B",
    abcProfit: "B",
    abcRevenue: "A",
    barcode: "4780012345004",
    brand: "UZUM Home",
    category: "Дом и кухня",
    status: "active",
    availability: "excess" as AvailabilityStatus,
  },
  {
    id: "SKU-005",
    name: "Набор косметики Premium",
    article: "COS-PRM-005",
    price: 178000,
    sales: 432,
    returns: 5,
    revenue: 76896000,
    lostRevenue: 890000,
    turnover: 0,
    stock: 0,
    endsIn: "—",
    costPrice: 89000,
    uzumCommission: 17800,
    uzumLogistics: 5000,
    abcOrders: "C",
    abcProfit: "B",
    abcRevenue: "C",
    barcode: "4780012345005",
    brand: "Beauty Plus",
    category: "Красота",
    status: "out_of_stock",
    availability: "out_of_stock" as AvailabilityStatus,
  },
  {
    id: "SKU-006",
    name: "Умные часы UZUM Watch",
    article: "WCH-UZ-006",
    price: 389000,
    sales: 654,
    returns: 18,
    revenue: 254406000,
    lostRevenue: 3890000,
    turnover: 9.1,
    stock: 178,
    endsIn: "32 дня",
    costPrice: 195000,
    uzumCommission: 38900,
    uzumLogistics: 8000,
    abcOrders: "A",
    abcProfit: "A",
    abcRevenue: "A",
    barcode: "4780012345006",
    brand: "UZUM Tech",
    category: "Электроника",
    status: "active",
    availability: "excess" as AvailabilityStatus,
  },
  {
    id: "SKU-007",
    name: "Блендер UZUM Power",
    article: "BLN-PWR-007",
    price: 145000,
    sales: 321,
    returns: 7,
    revenue: 46545000,
    lostRevenue: 1450000,
    turnover: 7.4,
    stock: 67,
    endsIn: "14 дней",
    costPrice: null,
    uzumCommission: 14500,
    uzumLogistics: 15000,
    abcOrders: "C",
    abcProfit: "C",
    abcRevenue: "C",
    barcode: "4780012345007",
    brand: "UZUM Home",
    category: "Дом и кухня",
    status: "low_stock",
    availability: "needs_supply" as AvailabilityStatus,
  },
  {
    id: "SKU-008",
    name: "Крем для лица Hydra+",
    article: "CRM-HYD-008",
    price: 89000,
    sales: 567,
    returns: 3,
    revenue: 50463000,
    lostRevenue: 445000,
    turnover: 18.9,
    stock: 289,
    endsIn: "67 дней",
    costPrice: 35000,
    uzumCommission: 8900,
    uzumLogistics: 3000,
    abcOrders: "B",
    abcProfit: "A",
    abcRevenue: "B",
    barcode: "4780012345008",
    brand: "Beauty Plus",
    category: "Красота",
    status: "active",
    availability: "excess" as AvailabilityStatus,
  },
];

type SortField = 
  | "name" 
  | "article" 
  | "price" 
  | "sales" 
  | "returns" 
  | "revenue" 
  | "lostRevenue" 
  | "turnover" 
  | "stock" 
  | "endsIn" 
  | "costPrice" 
  | "uzumCommission" 
  | "uzumLogistics" 
  | "abcOrders" 
  | "abcProfit" 
  | "abcRevenue" 
  | "barcode" 
  | "brand" 
  | "category";

type SortDirection = "asc" | "desc" | null;

export function ProductsView() {
  const [selectedProducts, setSelectedProducts] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [groupBy, setGroupBy] = useState<string | null>(null);
  const [selectedProduct, setSelectedProduct] = useState<typeof products[0] | null>(null);
  const [sortField, setSortField] = useState<SortField | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat("ru-RU").format(price) + " сум";
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat("ru-RU").format(num);
  };

  const getAvailabilityBadge = (availability: AvailabilityStatus) => {
    switch (availability) {
      case "excess":
        return <Badge className="bg-success/10 text-success hover:bg-success/20 text-xs">Избыток</Badge>;
      case "out_of_stock":
        return <Badge className="bg-destructive/10 text-destructive hover:bg-destructive/20 text-xs">Нет на складе</Badge>;
      case "needs_supply":
        return <Badge className="bg-warning/10 text-warning hover:bg-warning/20 text-xs">Нужна поставка</Badge>;
      default:
        return null;
    }
  };

  const getAbcBadge = (abc: string) => {
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

  const toggleSelectAll = () => {
    if (selectedProducts.length === sortedProducts.length) {
      setSelectedProducts([]);
    } else {
      setSelectedProducts(sortedProducts.map((p) => p.id));
    }
  };

  const toggleSelect = (id: string) => {
    setSelectedProducts((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    );
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

  const sortedProducts = [...products].sort((a, b) => {
    if (!sortField || !sortDirection) return 0;

    let aValue: any = a[sortField];
    let bValue: any = b[sortField];

    // Handle null values
    if (aValue === null) aValue = sortDirection === "asc" ? Infinity : -Infinity;
    if (bValue === null) bValue = sortDirection === "asc" ? Infinity : -Infinity;

    // String comparison
    if (typeof aValue === "string" && typeof bValue === "string") {
      return sortDirection === "asc" 
        ? aValue.localeCompare(bValue, "ru") 
        : bValue.localeCompare(aValue, "ru");
    }

    // Number comparison
    if (sortDirection === "asc") {
      return aValue > bValue ? 1 : -1;
    } else {
      return aValue < bValue ? 1 : -1;
    }
  });

  const handleExportXLSX = () => {
    if (selectedProducts.length === 0) {
      toast.error("Выберите товары для выгрузки");
      return;
    }

    const selectedData = sortedProducts
      .filter((p) => selectedProducts.includes(p.id))
      .map((p) => ({
        "Наименование": p.name,
        "Артикул": p.article,
        "Цена": p.price,
        "Продажи": p.sales,
        "Возвраты": p.returns,
        "Выручка": p.revenue,
        "Упущ. выручка": p.lostRevenue,
        "Оборачиваемость": p.turnover,
        "Остаток": p.stock,
        "Закончится": p.endsIn,
        "Себестоимость": p.costPrice || "",
        "Наличие": p.availability === "excess" ? "Избыток" : p.availability === "out_of_stock" ? "Нет на складе" : "Нужна поставка",
        "Комиссия UZUM": p.uzumCommission,
        "Логистика UZUM": p.uzumLogistics,
        "ABC заказы": p.abcOrders,
        "ABC прибыль": p.abcProfit,
        "ABC выручка": p.abcRevenue,
        "Штрихкод": p.barcode,
        "Бренд": p.brand,
        "Категория": p.category,
      }));

    const worksheet = XLSX.utils.json_to_sheet(selectedData);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Товары");
    XLSX.writeFile(workbook, `товары_${new Date().toISOString().split("T")[0]}.xlsx`);
    toast.success(`Выгружено ${selectedProducts.length} товаров`);
  };

  // If a product is selected, show the detail view
  if (selectedProduct) {
    return (
      <ProductDetailView 
        product={selectedProduct} 
        onBack={() => setSelectedProduct(null)} 
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

        <Select defaultValue="all">
          <SelectTrigger className="w-40 bg-background">
            <SelectValue placeholder="Категория" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Все категории</SelectItem>
            <SelectItem value="electronics">Электроника</SelectItem>
            <SelectItem value="home">Дом и кухня</SelectItem>
            <SelectItem value="beauty">Красота</SelectItem>
          </SelectContent>
        </Select>

        <Select defaultValue="all">
          <SelectTrigger className="w-40 bg-background">
            <SelectValue placeholder="Наличие" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Все</SelectItem>
            <SelectItem value="excess">Избыток</SelectItem>
            <SelectItem value="out_of_stock">Нет на складе</SelectItem>
            <SelectItem value="needs_supply">Нужна поставка</SelectItem>
          </SelectContent>
        </Select>

        <div className="flex-1" />

        {selectedProducts.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              Выбрано: {selectedProducts.length}
            </span>
          </div>
        )}

        <Button 
          variant="outline" 
          size="sm"
          onClick={handleExportXLSX}
          disabled={selectedProducts.length === 0}
        >
          <Download className="w-4 h-4 mr-2" />
          Выгрузить в XLSX
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm">
              <Settings className="w-4 h-4 mr-2" />
              Настройки
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-64">
            <DropdownMenuItem onClick={() => setGroupBy(groupBy === "size" ? null : "size")}>
              <Layers className="w-4 h-4 mr-2" />
              Сгруппировать по размерам
              {groupBy === "size" && <span className="ml-auto text-primary">✓</span>}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setGroupBy(groupBy === "color" ? null : "color")}>
              <Layers className="w-4 h-4 mr-2" />
              Сгруппировать по цветам
              {groupBy === "color" && <span className="ml-auto text-primary">✓</span>}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setGroupBy(groupBy === "all" ? null : "all")}>
              <Layers className="w-4 h-4 mr-2" />
              Сгруппировать по всем хар-кам
              {groupBy === "all" && <span className="ml-auto text-primary">✓</span>}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {groupBy && (
        <div className="text-sm text-muted-foreground">
          Группировка: <span className="text-primary font-medium">
            {groupBy === "size" ? "по размерам" : groupBy === "color" ? "по цветам" : "по всем характеристикам"}
          </span>
        </div>
      )}

      {/* Products Table */}
      <div className="data-table animate-fade-in overflow-hidden rounded-lg border border-border">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent bg-muted/30">
                <TableHead className="w-10 sticky left-0 bg-muted/30 z-10">
                  <Checkbox
                    checked={selectedProducts.length === sortedProducts.length && sortedProducts.length > 0}
                    onCheckedChange={toggleSelectAll}
                  />
                </TableHead>
                <SortableHeader field="name" className="min-w-[200px] sticky left-10 bg-muted/30 z-10">
                  Наименование
                </SortableHeader>
                <SortableHeader field="article" className="min-w-[100px]">
                  Артикул
                </SortableHeader>
                <SortableHeader field="price" className="text-right min-w-[100px]">
                  Цена
                </SortableHeader>
                <SortableHeader field="sales" className="text-right min-w-[80px]">
                  Продажи
                </SortableHeader>
                <SortableHeader field="returns" className="text-right min-w-[80px]">
                  Возвраты
                </SortableHeader>
                <SortableHeader field="revenue" className="text-right min-w-[120px]">
                  Выручка
                </SortableHeader>
                <SortableHeader field="lostRevenue" className="text-right min-w-[120px]">
                  Упущ. выручка
                </SortableHeader>
                <SortableHeader field="turnover" className="text-right min-w-[100px]">
                  Оборач-ть
                </SortableHeader>
                <SortableHeader field="stock" className="text-right min-w-[120px]">
                  Остаток
                </SortableHeader>
                <SortableHeader field="endsIn" className="text-right min-w-[100px]">
                  Закончится
                </SortableHeader>
                <TableHead className="text-center min-w-[120px]">
                  Наличие
                </TableHead>
                <SortableHeader field="costPrice" className="text-right min-w-[150px]">
                  Себестоимость
                </SortableHeader>
                <SortableHeader field="uzumCommission" className="text-right min-w-[100px]">
                  Комиссия
                </SortableHeader>
                <SortableHeader field="uzumLogistics" className="text-right min-w-[100px]">
                  Логистика
                </SortableHeader>
                <SortableHeader field="abcOrders" className="text-center min-w-[80px]">
                  ABC заказы
                </SortableHeader>
                <SortableHeader field="abcProfit" className="text-center min-w-[80px]">
                  ABC прибыль
                </SortableHeader>
                <SortableHeader field="abcRevenue" className="text-center min-w-[80px]">
                  ABC выручка
                </SortableHeader>
                <SortableHeader field="barcode" className="min-w-[130px]">
                  Штрихкод
                </SortableHeader>
                <SortableHeader field="brand" className="min-w-[100px]">
                  Бренд
                </SortableHeader>
                <SortableHeader field="category" className="min-w-[100px]">
                  Категория
                </SortableHeader>
                <TableHead className="w-10"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedProducts.map((product) => (
                <TableRow
                  key={product.id}
                  className={cn(
                    "cursor-pointer hover:bg-muted/50",
                    selectedProducts.includes(product.id) && "bg-primary/5"
                  )}
                  onClick={() => setSelectedProduct(product)}
                >
                  <TableCell className="sticky left-0 bg-card z-10" onClick={(e) => e.stopPropagation()}>
                    <Checkbox
                      checked={selectedProducts.includes(product.id)}
                      onCheckedChange={() => toggleSelect(product.id)}
                    />
                  </TableCell>
                  <TableCell className="sticky left-10 bg-card z-10">
                    <div className="min-w-0">
                      <p className="font-medium text-foreground truncate">{product.name}</p>
                      <p className="text-xs text-muted-foreground">{product.id}</p>
                    </div>
                  </TableCell>
                  <TableCell className="text-muted-foreground text-sm">{product.article}</TableCell>
                  <TableCell className="text-right font-medium">
                    {formatPrice(product.price)}
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {formatNumber(product.sales)}
                  </TableCell>
                  <TableCell className="text-right text-muted-foreground">
                    {formatNumber(product.returns)}
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {formatPrice(product.revenue)}
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {formatPrice(product.lostRevenue)}
                  </TableCell>
                  <TableCell className="text-right">
                    {product.turnover > 0 ? `${product.turnover}x` : "—"}
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {formatNumber(product.stock)}
                  </TableCell>
                  <TableCell className="text-right text-muted-foreground">
                    {product.endsIn}
                  </TableCell>
                  <TableCell className="text-center">
                    {getAvailabilityBadge(product.availability)}
                  </TableCell>
                  <TableCell className="text-right">
                    {product.costPrice ? (
                      <span className="font-medium">{formatPrice(product.costPrice)}</span>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right text-muted-foreground">
                    {formatPrice(product.uzumCommission)}
                  </TableCell>
                  <TableCell className="text-right text-muted-foreground">
                    {formatPrice(product.uzumLogistics)}
                  </TableCell>
                  <TableCell className="text-center">
                    {getAbcBadge(product.abcOrders)}
                  </TableCell>
                  <TableCell className="text-center">
                    {getAbcBadge(product.abcProfit)}
                  </TableCell>
                  <TableCell className="text-center">
                    {getAbcBadge(product.abcRevenue)}
                  </TableCell>
                  <TableCell className="text-muted-foreground text-sm font-mono">
                    {product.barcode}
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary" className="font-normal text-xs">
                      {product.brand}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="font-normal text-xs">
                      {product.category}
                    </Badge>
                  </TableCell>
                  <TableCell onClick={(e) => e.stopPropagation()}>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <MoreHorizontal className="w-4 h-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => setSelectedProduct(product)}>
                          <Eye className="w-4 h-4 mr-2" />
                          Просмотр
                        </DropdownMenuItem>
                        <DropdownMenuItem>
                          <Edit className="w-4 h-4 mr-2" />
                          Редактировать
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem className="text-destructive">
                          <Trash2 className="w-4 h-4 mr-2" />
                          Удалить
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}
