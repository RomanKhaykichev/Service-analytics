import { TrendingUp, TrendingDown, Flame, Eye, Star, ArrowUpRight } from "lucide-react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Breadcrumb } from "@/components/shared/Breadcrumb";
import { FilterBar } from "@/components/dashboard/FilterBar";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const trendingProducts = [
  {
    id: 1,
    name: "UZUM Smart Kettle Pro",
    category: "Электроника",
    price: 189000,
    growth: 35,
    views: 12400,
    rating: 4.8,
    trend: "hot",
  },
  {
    id: 2,
    name: "Умные часы UZUM Watch",
    category: "Электроника",
    price: 389000,
    growth: 28,
    views: 9800,
    rating: 4.9,
    trend: "hot",
  },
  {
    id: 3,
    name: "Крем для лица Hydra+",
    category: "Красота",
    price: 89000,
    growth: 22,
    views: 7600,
    rating: 4.6,
    trend: "up",
  },
  {
    id: 4,
    name: "Блендер UZUM Power",
    category: "Дом и кухня",
    price: 145000,
    growth: -8,
    views: 4200,
    rating: 4.3,
    trend: "down",
  },
  {
    id: 5,
    name: "UZUM Fitness Band Plus",
    category: "Электроника",
    price: 156000,
    growth: 18,
    views: 8900,
    rating: 4.7,
    trend: "up",
  },
  {
    id: 6,
    name: "Набор косметики Premium",
    category: "Красота",
    price: 178000,
    growth: 15,
    views: 6300,
    rating: 4.5,
    trend: "up",
  },
];

const categoryHeatmap = [
  { name: "Электроника", growth: 24, views: 45000, color: "bg-success" },
  { name: "Красота", growth: 18, views: 32000, color: "bg-success/80" },
  { name: "Дом и кухня", growth: 12, views: 28000, color: "bg-accent" },
  { name: "Одежда", growth: 5, views: 21000, color: "bg-warning" },
  { name: "Спорт", growth: -3, views: 15000, color: "bg-destructive/60" },
];

const opportunities = [
  {
    title: "Умные устройства для дома",
    description: "Низкая конкуренция, высокий спрос",
    potential: "Высокий",
    competition: "Низкая",
  },
  {
    title: "Органическая косметика",
    description: "Растущий тренд, маржа 40%+",
    potential: "Средний",
    competition: "Средняя",
  },
  {
    title: "Фитнес-аксессуары",
    description: "Сезонный рост в январе",
    potential: "Высокий",
    competition: "Низкая",
  },
];

const formatPrice = (price: number) => {
  return new Intl.NumberFormat("ru-RU").format(price) + " сум";
};

const Trends = () => {
  return (
    <MainLayout>
      <Breadcrumb items={[{ label: "Тренды" }]} />

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Тренды рынка</h1>
          <p className="text-muted-foreground">
            Анализ трендов и перспективных направлений
          </p>
        </div>
      </div>

      <FilterBar />

      {/* Trending Products Grid */}
      <section className="mt-6 mb-8">
        <h2 className="text-lg font-semibold text-foreground mb-4">
          Топ трендовые товары
        </h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {trendingProducts.map((product) => (
            <div
              key={product.id}
              className="kpi-card group cursor-pointer hover:border-primary/30"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="w-16 h-16 rounded-lg bg-muted flex items-center justify-center text-xs text-muted-foreground">
                  IMG
                </div>
                <div
                  className={cn(
                    "flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium",
                    product.trend === "hot" && "bg-destructive/10 text-destructive",
                    product.trend === "up" && "bg-success/10 text-success",
                    product.trend === "down" && "bg-muted text-muted-foreground"
                  )}
                >
                  {product.trend === "hot" && <Flame className="w-3 h-3" />}
                  {product.trend === "up" && <TrendingUp className="w-3 h-3" />}
                  {product.trend === "down" && <TrendingDown className="w-3 h-3" />}
                  <span>
                    {product.growth > 0 ? "+" : ""}
                    {product.growth}%
                  </span>
                </div>
              </div>

              <h3 className="font-medium text-foreground mb-1 group-hover:text-primary transition-colors">
                {product.name}
              </h3>
              <p className="text-sm text-muted-foreground mb-3">{product.category}</p>

              <div className="flex items-center justify-between text-sm">
                <span className="font-semibold text-foreground">
                  {formatPrice(product.price)}
                </span>
                <div className="flex items-center gap-3 text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Eye className="w-3 h-3" />
                    {(product.views / 1000).toFixed(1)}K
                  </span>
                  <span className="flex items-center gap-1">
                    <Star className="w-3 h-3 fill-warning text-warning" />
                    {product.rating}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Category Heatmap + Opportunities */}
      <section className="grid lg:grid-cols-2 gap-6">
        {/* Category Heatmap */}
        <div className="chart-container">
          <h3 className="font-semibold text-foreground mb-4">
            Тепловая карта категорий
          </h3>
          <div className="space-y-3">
            {categoryHeatmap.map((category) => (
              <div key={category.name} className="flex items-center gap-3">
                <div className="w-28 text-sm font-medium text-foreground">
                  {category.name}
                </div>
                <div className="flex-1 h-8 rounded-lg bg-muted overflow-hidden relative">
                  <div
                    className={cn("h-full rounded-lg transition-all", category.color)}
                    style={{ width: `${Math.min(Math.abs(category.growth) * 4, 100)}%` }}
                  />
                  <div className="absolute inset-0 flex items-center px-3">
                    <span className="text-xs font-medium text-foreground">
                      {category.growth > 0 ? "+" : ""}
                      {category.growth}%
                    </span>
                  </div>
                </div>
                <div className="w-20 text-right text-sm text-muted-foreground">
                  {(category.views / 1000).toFixed(0)}K
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Opportunities */}
        <div className="chart-container">
          <div className="flex items-center gap-2 mb-4">
            <ArrowUpRight className="w-5 h-5 text-success" />
            <h3 className="font-semibold text-foreground">
              Открывающиеся возможности
            </h3>
          </div>
          <div className="space-y-3">
            {opportunities.map((opp, index) => (
              <div
                key={index}
                className="p-4 rounded-lg border border-border bg-muted/30 hover:bg-muted/50 transition-colors cursor-pointer"
              >
                <div className="flex items-start justify-between mb-2">
                  <h4 className="font-medium text-foreground">{opp.title}</h4>
                  <Badge
                    className={cn(
                      "text-xs",
                      opp.potential === "Высокий"
                        ? "bg-success/10 text-success"
                        : "bg-warning/10 text-warning"
                    )}
                  >
                    {opp.potential}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground mb-2">{opp.description}</p>
                <div className="flex items-center gap-4 text-xs">
                  <span className="text-muted-foreground">
                    Конкуренция:{" "}
                    <span
                      className={cn(
                        "font-medium",
                        opp.competition === "Низкая" ? "text-success" : "text-warning"
                      )}
                    >
                      {opp.competition}
                    </span>
                  </span>
                </div>
              </div>
            ))}
          </div>
          <Button variant="outline" className="w-full mt-4">
            Показать все возможности
          </Button>
        </div>
      </section>
    </MainLayout>
  );
};

export default Trends;
