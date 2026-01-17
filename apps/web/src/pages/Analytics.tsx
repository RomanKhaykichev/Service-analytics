import {
  ShoppingCart,
  TrendingUp,
  DollarSign,
  BarChart3,
  Target,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
} from "lucide-react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Breadcrumb } from "@/components/shared/Breadcrumb";
import { KPICard } from "@/components/dashboard/KPICard";
import { FilterBar } from "@/components/dashboard/FilterBar";
import { RevenueChart } from "@/components/dashboard/RevenueChart";
import { CategoryChart } from "@/components/dashboard/CategoryChart";
import { TopProductsTable } from "@/components/dashboard/TopProductsTable";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from "recharts";

const trafficData = [
  { name: "Органика", value: 45, color: "hsl(var(--primary))" },
  { name: "Реклама", value: 30, color: "hsl(var(--accent))" },
  { name: "Прямые", value: 15, color: "hsl(var(--warning))" },
  { name: "Соц. сети", value: 10, color: "hsl(var(--chart-4))" },
];

const kpiData = [
  {
    title: "Выручка",
    value: "3,2M сум",
    change: 15.2,
    icon: DollarSign,
    iconColor: "text-primary",
    trend: "up" as const,
    sparkline: [45, 52, 38, 65, 72, 85, 92],
  },
  {
    title: "Заказы",
    value: "8 275",
    change: 8.3,
    icon: ShoppingCart,
    iconColor: "text-accent",
    trend: "up" as const,
    sparkline: [32, 45, 38, 52, 48, 62, 58],
  },
  {
    title: "Прибыль",
    value: "1,3M сум",
    change: 5.8,
    icon: TrendingUp,
    iconColor: "text-success",
    trend: "up" as const,
    sparkline: [42, 38, 45, 42, 48, 52, 55],
  },
  {
    title: "Рентабельность",
    value: "40,3%",
    change: 2.1,
    icon: Target,
    iconColor: "text-warning",
    trend: "up" as const,
    sparkline: [38, 42, 45, 48, 52, 48, 55],
  },
  {
    title: "ROI",
    value: "107,2%",
    change: -3.5,
    icon: BarChart3,
    iconColor: "text-primary",
    trend: "down" as const,
    sparkline: [55, 52, 48, 45, 42, 40, 38],
  },
];

const anomalies = [
  {
    type: "warning",
    title: "Падение конверсии",
    description: "Категория 'Одежда' показала снижение на 12%",
    time: "2 часа назад",
  },
  {
    type: "success",
    title: "Рост продаж",
    description: "'UZUM Smart Kettle' вырос на 35% за неделю",
    time: "5 часов назад",
  },
];

const Analytics = () => {
  return (
    <MainLayout>
      <Breadcrumb items={[{ label: "Аналитика" }]} />

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Дашборд аналитики</h1>
          <p className="text-muted-foreground">Обзор ключевых метрик вашего бизнеса</p>
        </div>
      </div>

      {/* Filter Bar */}
      <FilterBar />

      {/* KPI Cards */}
      <section className="mt-6 mb-8">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {kpiData.map((kpi) => (
            <KPICard key={kpi.title} {...kpi} />
          ))}
        </div>
      </section>

      {/* Charts Row */}
      <section className="grid lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2">
          <RevenueChart />
        </div>
        
        {/* Traffic Sources */}
        <div className="chart-container animate-fade-in">
          <div className="mb-4">
            <h3 className="font-semibold text-foreground">Источники трафика</h3>
            <p className="text-sm text-muted-foreground">Распределение посещений</p>
          </div>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={trafficData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {trafficData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "8px",
                  }}
                  formatter={(value: number) => [`${value}%`, ""]}
                />
                <Legend
                  formatter={(value) => (
                    <span className="text-sm text-foreground">{value}</span>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      {/* Category Chart + Anomalies */}
      <section className="grid lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2">
          <CategoryChart />
        </div>

        {/* Anomalies */}
        <div className="chart-container animate-fade-in">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-5 h-5 text-warning" />
            <h3 className="font-semibold text-foreground">Аномалии</h3>
          </div>
          <div className="space-y-3">
            {anomalies.map((anomaly, index) => (
              <div
                key={index}
                className="p-3 rounded-lg border border-border bg-muted/30 hover:bg-muted/50 transition-colors cursor-pointer"
              >
                <div className="flex items-start gap-3">
                  {anomaly.type === "warning" ? (
                    <ArrowDownRight className="w-5 h-5 text-destructive mt-0.5" />
                  ) : (
                    <ArrowUpRight className="w-5 h-5 text-success mt-0.5" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-foreground text-sm">
                      {anomaly.title}
                    </p>
                    <p className="text-sm text-muted-foreground mt-0.5">
                      {anomaly.description}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {anomaly.time}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Top Products */}
      <section>
        <TopProductsTable />
      </section>
    </MainLayout>
  );
};

export default Analytics;
