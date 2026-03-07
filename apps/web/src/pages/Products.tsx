import { useState } from "react";
import {
  Search,
  Filter,
  Download,
  Plus,
  MoreHorizontal,
  Eye,
  Edit,
  Trash2,
  Settings,
  Layers,
} from "lucide-react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Breadcrumb } from "@/components/shared/Breadcrumb";
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
import { useLanguage } from "@/contexts/LanguageContext";

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
  },
];

const Products = () => {
  const { t } = useLanguage();
  const [selectedProducts, setSelectedProducts] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [productCosts, setProductCosts] = useState<Record<string, number | null>>(() => {
    const initial: Record<string, number | null> = {};
    products.forEach((p) => {
      initial[p.id] = p.costPrice;
    });
    return initial;
  });
  const [editingCost, setEditingCost] = useState<string | null>(null);
  const [tempCostValue, setTempCostValue] = useState("");
  const [groupBy, setGroupBy] = useState<string | null>(null);

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat("ru-RU").format(price) + " " + t("common.sum");
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat("ru-RU").format(num);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "active":
        return <Badge className="bg-success/10 text-success hover:bg-success/20 text-xs">В наличии</Badge>;
      case "low_stock":
        return <Badge className="bg-warning/10 text-warning hover:bg-warning/20 text-xs">Мало</Badge>;
      case "out_of_stock":
        return <Badge className="bg-destructive/10 text-destructive hover:bg-destructive/20 text-xs">Нет</Badge>;
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
    if (selectedProducts.length === products.length) {
      setSelectedProducts([]);
    } else {
      setSelectedProducts(products.map((p) => p.id));
    }
  };

  const toggleSelect = (id: string) => {
    setSelectedProducts((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    );
  };

  const handleAddCost = (productId: string) => {
    setEditingCost(productId);
    setTempCostValue(productCosts[productId]?.toString() || "");
  };

  const handleSaveCost = (productId: string) => {
    const value = parseInt(tempCostValue);
    if (!isNaN(value) && value > 0) {
      setProductCosts((prev) => ({ ...prev, [productId]: value }));
    }
    setEditingCost(null);
    setTempCostValue("");
  };

  const handleCancelCost = () => {
    setEditingCost(null);
    setTempCostValue("");
  };

  return (
    <MainLayout>
      <Breadcrumb items={[{ label: "Товары" }]} />

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Товары</h1>
          <p className="text-muted-foreground">
            {products.length} товаров в каталоге
            {groupBy && (
              <span className="ml-2 text-primary">
                • Группировка: {groupBy === "size" ? "по размерам" : groupBy === "color" ? "по цветам" : "по всем характеристикам"}
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm">
                <Settings className="w-4 h-4 mr-2" />
                Настройки
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
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
          <Button>
            <Plus className="w-4 h-4 mr-2" />
            Добавить товар
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="filter-bar mb-6">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder={t('search.byNameArticle')}
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
          <SelectTrigger className="w-36 bg-background">
            <SelectValue placeholder="Статус" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Все статусы</SelectItem>
            <SelectItem value="active">В наличии</SelectItem>
            <SelectItem value="low_stock">Мало</SelectItem>
            <SelectItem value="out_of_stock">Нет в наличии</SelectItem>
          </SelectContent>
        </Select>

        <div className="flex-1" />

        {selectedProducts.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              Выбрано: {selectedProducts.length}
            </span>
            <Button variant="outline" size="sm">
              <Download className="w-4 h-4 mr-2" />
              Экспорт
            </Button>
          </div>
        )}

        <Button variant="outline" size="sm">
          <Filter className="w-4 h-4 mr-2" />
          Фильтры
        </Button>
      </div>

      {/* Products Table */}
      <div className="data-table animate-fade-in overflow-hidden">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="w-10 sticky left-0 bg-card z-10">
                  <Checkbox
                    checked={selectedProducts.length === products.length}
                    onCheckedChange={toggleSelectAll}
                  />
                </TableHead>
                <TableHead className="min-w-[200px] sticky left-10 bg-card z-10">Наименование</TableHead>
                <TableHead className="min-w-[100px]">Артикул</TableHead>
                <TableHead className="text-right min-w-[100px]">Цена</TableHead>
                <TableHead className="text-right min-w-[80px]">Продажи</TableHead>
                <TableHead className="text-right min-w-[80px]">Возвраты</TableHead>
                <TableHead className="text-right min-w-[120px]">Выручка</TableHead>
                <TableHead className="text-right min-w-[120px]">Упущ. выручка</TableHead>
                <TableHead className="text-right min-w-[100px]">Оборач-ть</TableHead>
                <TableHead className="text-right min-w-[100px]">Остаток</TableHead>
                <TableHead className="text-right min-w-[100px]">Закончится</TableHead>
                <TableHead className="text-right min-w-[150px]">Себестоимость</TableHead>
                <TableHead className="text-right min-w-[100px]">Комиссия</TableHead>
                <TableHead className="text-right min-w-[100px]">Логистика</TableHead>
                <TableHead className="text-center min-w-[70px]">ABC заказы</TableHead>
                <TableHead className="text-center min-w-[70px]">ABC прибыль</TableHead>
                <TableHead className="text-center min-w-[70px]">ABC выручка</TableHead>
                <TableHead className="min-w-[130px]">Штрихкод</TableHead>
                <TableHead className="min-w-[100px]">Бренд</TableHead>
                <TableHead className="min-w-[100px]">Категория</TableHead>
                <TableHead className="w-10"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {products.map((product) => (
                <TableRow
                  key={product.id}
                  className={cn(
                    "cursor-pointer",
                    selectedProducts.includes(product.id) && "bg-primary/5"
                  )}
                >
                  <TableCell className="sticky left-0 bg-card z-10">
                    <Checkbox
                      checked={selectedProducts.includes(product.id)}
                      onCheckedChange={() => toggleSelect(product.id)}
                    />
                  </TableCell>
                  <TableCell className="sticky left-10 bg-card z-10">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center text-xs font-medium text-muted-foreground shrink-0">
                        IMG
                      </div>
                      <div className="min-w-0">
                        <p className="font-medium text-foreground truncate">{product.name}</p>
                        <p className="text-xs text-muted-foreground">{product.id}</p>
                      </div>
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
                  <TableCell className="text-right font-medium text-success">
                    {formatPrice(product.revenue)}
                  </TableCell>
                  <TableCell className="text-right text-destructive">
                    {formatPrice(product.lostRevenue)}
                  </TableCell>
                  <TableCell className="text-right">
                    {product.turnover > 0 ? `${product.turnover}x` : "—"}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <span className="font-medium">{product.stock}</span>
                      {getStatusBadge(product.status)}
                    </div>
                  </TableCell>
                  <TableCell className="text-right text-muted-foreground">
                    {product.endsIn}
                  </TableCell>
                  <TableCell className="text-right">
                    {editingCost === product.id ? (
                      <div className="flex items-center gap-1 justify-end">
                        <Input
                          type="number"
                          value={tempCostValue}
                          onChange={(e) => setTempCostValue(e.target.value)}
                          className="w-24 h-7 text-xs"
                          placeholder="Сумма"
                          autoFocus
                        />
                        <Button size="sm" variant="ghost" className="h-7 px-2 text-xs" onClick={() => handleSaveCost(product.id)}>
                          ✓
                        </Button>
                        <Button size="sm" variant="ghost" className="h-7 px-2 text-xs" onClick={handleCancelCost}>
                          ✕
                        </Button>
                      </div>
                    ) : productCosts[product.id] ? (
                      <span className="font-medium">{formatPrice(productCosts[product.id]!)}</span>
                    ) : (
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7 text-xs text-primary border-primary hover:bg-primary/10"
                        onClick={() => handleAddCost(product.id)}
                      >
                        Добавить
                      </Button>
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
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <MoreHorizontal className="w-4 h-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem>
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
    </MainLayout>
  );
};

export default Products;
