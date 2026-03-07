import { Star, TrendingUp, TrendingDown, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { useLanguage } from "@/contexts/LanguageContext";

const products = [
  {
    id: "SKU-001",
    name: "UZUM Smart Kettle Pro",
    category: "Электроника",
    price: 189000,
    sales: 1245,
    conversion: 4.2,
    rating: 4.8,
    reviews: 324,
    trend: "up" as const,
  },
  {
    id: "SKU-002",
    name: "UZUM Wireless Earbuds X5",
    category: "Электроника",
    price: 245000,
    sales: 987,
    conversion: 3.8,
    rating: 4.6,
    reviews: 256,
    trend: "up" as const,
  },
  {
    id: "SKU-003",
    name: "UZUM Fitness Band Plus",
    category: "Электроника",
    price: 156000,
    sales: 876,
    conversion: 5.1,
    rating: 4.7,
    reviews: 189,
    trend: "up" as const,
  },
  {
    id: "SKU-004",
    name: "Кухонный комбайн UZUM",
    category: "Дом и кухня",
    price: 425000,
    sales: 543,
    conversion: 2.9,
    rating: 4.4,
    reviews: 87,
    trend: "down" as const,
  },
  {
    id: "SKU-005",
    name: "Набор косметики Premium",
    category: "Красота",
    price: 178000,
    sales: 432,
    conversion: 3.5,
    rating: 4.5,
    reviews: 156,
    trend: "neutral" as const,
  },
];

export function TopProductsTable() {
  const { t } = useLanguage();
  const formatPrice = (price: number) => {
    return new Intl.NumberFormat("ru-RU").format(price) + " " + t("common.sum");
  };

  return (
    <div className="chart-container animate-fade-in overflow-hidden">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-semibold text-foreground">Топ товары</h3>
          <p className="text-sm text-muted-foreground">Лидеры продаж за период</p>
        </div>
        <Button variant="ghost" size="sm">
          Все товары
          <ExternalLink className="w-4 h-4 ml-1" />
        </Button>
      </div>

      <div className="overflow-x-auto -mx-5">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="pl-5">Товар</TableHead>
              <TableHead>Категория</TableHead>
              <TableHead className="text-right">Цена</TableHead>
              <TableHead className="text-right">Продажи</TableHead>
              <TableHead className="text-right">Конверсия</TableHead>
              <TableHead className="text-right pr-5">Рейтинг</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {products.map((product) => (
              <TableRow key={product.id} className="cursor-pointer">
                <TableCell className="pl-5">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center text-xs font-medium text-muted-foreground">
                      IMG
                    </div>
                    <div>
                      <p className="font-medium text-foreground">{product.name}</p>
                      <p className="text-xs text-muted-foreground">{product.id}</p>
                    </div>
                  </div>
                </TableCell>
                <TableCell>
                  <Badge variant="secondary" className="font-normal">
                    {product.category}
                  </Badge>
                </TableCell>
                <TableCell className="text-right font-medium">
                  {formatPrice(product.price)}
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-1">
                    <span className="font-medium">{product.sales}</span>
                    {product.trend === "up" && (
                      <TrendingUp className="w-4 h-4 text-success" />
                    )}
                    {product.trend === "down" && (
                      <TrendingDown className="w-4 h-4 text-destructive" />
                    )}
                  </div>
                </TableCell>
                <TableCell className="text-right">
                  <span
                    className={cn(
                      "font-medium",
                      product.conversion >= 4 ? "text-success" : 
                      product.conversion >= 3 ? "text-foreground" : "text-warning"
                    )}
                  >
                    {product.conversion}%
                  </span>
                </TableCell>
                <TableCell className="text-right pr-5">
                  <div className="flex items-center justify-end gap-1">
                    <Star className="w-4 h-4 fill-warning text-warning" />
                    <span className="font-medium">{product.rating}</span>
                    <span className="text-muted-foreground">({product.reviews})</span>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
