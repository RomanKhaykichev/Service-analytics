import { Building2, TrendingUp, TrendingDown, Bell, ExternalLink, Eye } from "lucide-react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Breadcrumb } from "@/components/shared/Breadcrumb";
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
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

const competitors = [
  {
    id: 1,
    name: "ZetaMarket",
    categories: ["Электроника", "Дом"],
    priceRange: "50K - 500K",
    estimatedSales: 8500000,
    marketShare: 28,
    priceChange: -5,
    trend: "up",
  },
  {
    id: 2,
    name: "AlphaGoods",
    categories: ["Красота", "Одежда"],
    priceRange: "30K - 300K",
    estimatedSales: 6200000,
    marketShare: 21,
    priceChange: 0,
    trend: "neutral",
  },
  {
    id: 3,
    name: "NovaRetail",
    categories: ["Электроника"],
    priceRange: "100K - 800K",
    estimatedSales: 5100000,
    marketShare: 17,
    priceChange: 3,
    trend: "down",
  },
  {
    id: 4,
    name: "TechZone",
    categories: ["Электроника", "Спорт"],
    priceRange: "80K - 600K",
    estimatedSales: 4300000,
    marketShare: 14,
    priceChange: -2,
    trend: "up",
  },
];

const priceAlerts = [
  {
    competitor: "ZetaMarket",
    product: "Smart Kettle",
    oldPrice: 199000,
    newPrice: 189000,
    change: -5,
    time: "2 часа назад",
  },
  {
    competitor: "AlphaGoods",
    product: "Fitness Band",
    oldPrice: 145000,
    newPrice: 139000,
    change: -4,
    time: "5 часов назад",
  },
  {
    competitor: "TechZone",
    product: "Wireless Earbuds",
    oldPrice: 230000,
    newPrice: 245000,
    change: 7,
    time: "1 день назад",
  },
];

const formatSales = (sales: number) => {
  return (sales / 1000000).toFixed(1) + "M сум";
};

const formatPrice = (price: number) => {
  return new Intl.NumberFormat("ru-RU").format(price) + " сум";
};

const Competitors = () => {
  return (
    <MainLayout>
      <Breadcrumb items={[{ label: "Конкуренты" }]} />

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Анализ конкурентов</h1>
          <p className="text-muted-foreground">
            Мониторинг цен и активности конкурентов
          </p>
        </div>
        <Button>
          <Bell className="w-4 h-4 mr-2" />
          Настроить оповещения
        </Button>
      </div>

      {/* Competitors Table */}
      <div className="data-table animate-fade-in overflow-hidden mb-8">
        <div className="p-4 border-b border-border">
          <h3 className="font-semibold text-foreground">Список конкурентов</h3>
        </div>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead>Конкурент</TableHead>
                <TableHead>Категории</TableHead>
                <TableHead>Ценовой диапазон</TableHead>
                <TableHead className="text-right">Объём продаж (оценка)</TableHead>
                <TableHead className="text-right">Доля рынка</TableHead>
                <TableHead className="text-right">Изм. цен</TableHead>
                <TableHead className="w-12"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {competitors.map((competitor) => (
                <TableRow key={competitor.id} className="cursor-pointer">
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-primary-light flex items-center justify-center">
                        <Building2 className="w-5 h-5 text-primary" />
                      </div>
                      <span className="font-medium text-foreground">
                        {competitor.name}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {competitor.categories.map((cat) => (
                        <Badge key={cat} variant="secondary" className="text-xs">
                          {cat}
                        </Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {competitor.priceRange}
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {formatSales(competitor.estimatedSales)}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Progress value={competitor.marketShare} className="w-16 h-2" />
                      <span className="font-medium w-10">{competitor.marketShare}%</span>
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <span
                      className={cn(
                        "flex items-center justify-end gap-1 font-medium",
                        competitor.priceChange < 0 && "text-success",
                        competitor.priceChange > 0 && "text-destructive",
                        competitor.priceChange === 0 && "text-muted-foreground"
                      )}
                    >
                      {competitor.priceChange < 0 && <TrendingDown className="w-4 h-4" />}
                      {competitor.priceChange > 0 && <TrendingUp className="w-4 h-4" />}
                      {competitor.priceChange !== 0 && `${competitor.priceChange}%`}
                      {competitor.priceChange === 0 && "—"}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="icon">
                      <Eye className="w-4 h-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* Price Alerts */}
      <div className="chart-container">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-warning" />
            <h3 className="font-semibold text-foreground">Изменения цен</h3>
          </div>
          <Button variant="ghost" size="sm">
            Все уведомления
            <ExternalLink className="w-4 h-4 ml-1" />
          </Button>
        </div>

        <div className="space-y-3">
          {priceAlerts.map((alert, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-3 rounded-lg border border-border bg-muted/30 hover:bg-muted/50 transition-colors"
            >
              <div className="flex items-center gap-4">
                <div
                  className={cn(
                    "w-10 h-10 rounded-lg flex items-center justify-center",
                    alert.change < 0 ? "bg-success/10" : "bg-destructive/10"
                  )}
                >
                  {alert.change < 0 ? (
                    <TrendingDown className="w-5 h-5 text-success" />
                  ) : (
                    <TrendingUp className="w-5 h-5 text-destructive" />
                  )}
                </div>
                <div>
                  <p className="font-medium text-foreground">
                    {alert.competitor} — {alert.product}
                  </p>
                  <p className="text-sm text-muted-foreground">{alert.time}</p>
                </div>
              </div>
              <div className="text-right">
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground line-through text-sm">
                    {formatPrice(alert.oldPrice)}
                  </span>
                  <span className="font-semibold text-foreground">
                    {formatPrice(alert.newPrice)}
                  </span>
                </div>
                <span
                  className={cn(
                    "text-sm font-medium",
                    alert.change < 0 ? "text-success" : "text-destructive"
                  )}
                >
                  {alert.change > 0 ? "+" : ""}
                  {alert.change}%
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </MainLayout>
  );
};

export default Competitors;
