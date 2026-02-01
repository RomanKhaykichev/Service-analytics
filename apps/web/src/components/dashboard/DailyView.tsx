import { useState, useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { ChevronUp, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { useOrdersSalesDaily } from "@/hooks/useOrdersSalesDaily";
import { useDailySummary } from "@/hooks/useDailySummary";
import { format, startOfWeek, endOfWeek } from "date-fns";
import { ru } from "date-fns/locale";

interface DailyViewProps {
  viewMode?: string;
  periodCode?: string;
  shopId?: string | null;
  /** Shop name (string) from seller-storage for filtering by barcode */
  shop?: string | null;
}

// Конфигурация цветов серий графика (привязана к ключам метрик для стабильности)
const SERIES_COLORS: Record<string, string> = {
  orders: "#2563EB",    // Заказы - синий
  buyouts: "#16A34A",   // Выкупы - зелёный
  returns: "#DC2626",    // Возвраты - красный
  revenue: "#F59E0B",   // Выручка - оранжевый
  profit: "#7C3AED",    // Прибыль - фиолетовый
  avgCheck: "#06B6D4",  // Средний чек - голубой
};

const chartFilters = [
  { key: "orders", label: "Заказы", color: SERIES_COLORS.orders },
  { key: "buyouts", label: "Выкупы", color: SERIES_COLORS.buyouts },
  { key: "returns", label: "Возвраты", color: SERIES_COLORS.returns },
  { key: "revenue", label: "Выручка", color: SERIES_COLORS.revenue },
  { key: "profit", label: "Прибыль", color: SERIES_COLORS.profit },
  { key: "avgCheck", label: "Средний чек", color: SERIES_COLORS.avgCheck },
];

type SortDirection = "asc" | "desc" | null;
type SortColumn = string | null;

type GroupByType = "day" | "week" | "month";

export function DailyView({ viewMode = "day", periodCode = "30d", shopId = null, shop = null }: DailyViewProps) {
  // State for time grouping filter
  const [groupBy, setGroupBy] = useState<GroupByType>("day");
  
  // Load data from backend (filtered by shop when set)
  const { data: ordersSalesData, isLoading: loading, error } = useOrdersSalesDaily({ periodCode, shopId, shop, groupBy });
  const { data: dailySummaryData, isLoading: loadingTable, error: errorTable } = useDailySummary({ periodCode, shopId, shop });
  
  // Format date label based on grouping
  const formatDateLabel = (dateStr: string, grouping: GroupByType): string => {
    const date = new Date(dateStr);
    switch (grouping) {
      case "week": {
        // ISO week starts on Monday
        const weekStart = startOfWeek(date, { weekStartsOn: 1 });
        const weekEnd = endOfWeek(date, { weekStartsOn: 1 });
        return `${format(weekStart, "dd.MM")}–${format(weekEnd, "dd.MM")}`;
      }
      case "month":
        // Format as "MMM yyyy" (e.g., "Янв 2026")
        return format(date, "MMM yyyy", { locale: ru });
      case "day":
      default:
        return format(date, "dd.MM");
    }
  };
  
  // Transform data for chart: format dates based on grouping and map field names
  const chartData = useMemo(() => {
    if (!ordersSalesData?.points || ordersSalesData.points.length === 0) {
      return [];
    }
    return ordersSalesData.points.map((point) => {
      return {
        date: formatDateLabel(point.date, groupBy),
        orders: point.orders_qty,      // Заказы - метрика orders_qty
        buyouts: point.buyouts_qty,    // Выкупы - метрика buyouts_qty
        returns: point.returns_qty,
        revenue: point.revenue_sum,
        profit: point.profit_sum,
        avgCheck: point.avg_check,
      };
    });
  }, [ordersSalesData, groupBy]);
  const [activeFilters, setActiveFilters] = useState<string[]>(["orders", "revenue"]);
  const [sortColumn, setSortColumn] = useState<SortColumn>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);

  const toggleFilter = (key: string) => {
    setActiveFilters((prev) =>
      prev.includes(key) ? prev.filter((f) => f !== key) : [...prev, key]
    );
  };

  const handleSort = (column: SortColumn) => {
    if (sortColumn === column) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : prev === "desc" ? null : "asc"));
      if (sortDirection === "desc") setSortColumn(null);
    } else {
      setSortColumn(column);
      setSortDirection("asc");
    }
  };

  // Table data from API: map DailySummaryPoint to table row (date formatted for display)
  const tableRows = useMemo(() => {
    if (!dailySummaryData?.points?.length) return [];
    return dailySummaryData.points.map((p) => ({
      date: p.date,
      dateFormatted: format(new Date(p.date), "dd.MM.yyyy"),
      orders: p.orders,
      buys: p.buys,
      returns: p.returns,
      revenue: p.revenue,
      commission: p.commission,
      logistics: p.logistics,
      storage: p.storage,
      ads: p.ads,
      penalties: p.penalties,
      cogs: p.cogs,
      taxes: p.taxes,
      profit: p.profit,
    }));
  }, [dailySummaryData?.points]);

  const filteredAndSortedData = [...tableRows].sort((a, b) => {
      if (!sortColumn || !sortDirection) return 0;
      const aVal = sortColumn === "dateFormatted" ? a.date : a[sortColumn as keyof typeof a];
      const bVal = sortColumn === "dateFormatted" ? b.date : b[sortColumn as keyof typeof b];
      if (typeof aVal === "string" && typeof bVal === "string") {
        return sortDirection === "asc" ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      }
      if (typeof aVal === "number" && typeof bVal === "number") {
        return sortDirection === "asc" ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number);
      }
      return 0;
    });

  const formatNumber = (num: number) => num.toLocaleString("ru-RU");

  const columns = [
    { key: "dateFormatted", label: "Дата" },
    { key: "orders", label: "Заказы" },
    { key: "buys", label: "Выкупы" },
    { key: "returns", label: "Возвраты" },
    { key: "revenue", label: "Выручка" },
    { key: "commission", label: "Комиссия" },
    { key: "logistics", label: "Логистика" },
    { key: "storage", label: "Хранение" },
    { key: "ads", label: "Реклама" },
    { key: "penalties", label: "Штрафы" },
    { key: "cogs", label: "Себестоимость" },
    { key: "taxes", label: "Налоги" },
    { key: "profit", label: "Прибыль" },
  ];

  return (
    <div className="space-y-6">
      {/* Chart Section */}
      <div className="bg-card rounded-xl p-5 border border-border shadow-sm">
        {/* Header: title + grouping filter + metric buttons */}
        <div className="flex items-center gap-3 flex-wrap mb-4">
          {/* Left group: title + grouping filter */}
          <div className="flex items-center gap-2 flex-1 min-w-[320px]">
            <h3 className="font-semibold text-foreground">График заказов и продаж</h3>
            {/* Time grouping filter */}
            <div className="flex gap-1 border border-border rounded-md p-1 flex-shrink-0 whitespace-nowrap">
              <Button
                variant={groupBy === "day" ? "default" : "ghost"}
                size="sm"
                onClick={() => setGroupBy("day")}
                className="text-xs h-7"
              >
                Дни
              </Button>
              <Button
                variant={groupBy === "week" ? "default" : "ghost"}
                size="sm"
                onClick={() => setGroupBy("week")}
                className="text-xs h-7"
              >
                Недели
              </Button>
              <Button
                variant={groupBy === "month" ? "default" : "ghost"}
                size="sm"
                onClick={() => setGroupBy("month")}
                className="text-xs h-7"
              >
                Месяцы
              </Button>
            </div>
          </div>
          {/* Right group: metric filters */}
          <div className="flex items-center gap-2 ml-auto flex-wrap justify-end flex-shrink-0">
            {chartFilters.map((filter) => (
              <Button
                key={filter.key}
                variant={activeFilters.includes(filter.key) ? "default" : "outline"}
                size="sm"
                onClick={() => toggleFilter(filter.key)}
                className="text-xs"
                style={{
                  backgroundColor: activeFilters.includes(filter.key) ? filter.color : undefined,
                  borderColor: filter.color,
                  color: activeFilters.includes(filter.key) ? "white" : filter.color,
                }}
              >
                {filter.label}
              </Button>
            ))}
          </div>
        </div>

        <div className="h-80">
          {loading ? (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              Загрузка...
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-full text-destructive">
              Ошибка загрузки данных
            </div>
          ) : chartData.length === 0 ? (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              Нет данных за выбранный период
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis
                  dataKey="date"
                  tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                  axisLine={{ stroke: "hsl(var(--border))" }}
                />
                <YAxis
                  yAxisId="left"
                  tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                  axisLine={{ stroke: "hsl(var(--border))" }}
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                  axisLine={{ stroke: "hsl(var(--border))" }}
                  tickFormatter={(value) => value >= 1000000 ? `${(value / 1000000).toFixed(1)}M` : value >= 1000 ? `${(value / 1000).toFixed(0)}k` : value}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "8px",
                  }}
                  formatter={(value: number, name: string) => {
                    const filter = chartFilters.find((f) => f.key === name);
                    return [formatNumber(value), filter?.label || name];
                  }}
                />
                <Legend
                  formatter={(value) => {
                    const filter = chartFilters.find((f) => f.key === value);
                    return filter?.label || value;
                  }}
                />
                {chartFilters.map((filter) =>
                  activeFilters.includes(filter.key) ? (
                    <Line
                      key={filter.key}
                      yAxisId={["revenue", "avgCheck"].includes(filter.key) ? "right" : ["profit"].includes(filter.key) ? "right" : "left"}
                      type="monotone"
                      dataKey={filter.key}
                      stroke={filter.color}
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 4 }}
                    />
                  ) : null
                )}
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Table Section — Данные по дням from GET /api/charts/daily-summary */}
      <div className="bg-card rounded-xl p-5 border border-border shadow-sm">
        <h3 className="font-semibold text-foreground mb-4">Данные по дням</h3>
        <div className="overflow-x-auto">
          {loadingTable ? (
            <div className="py-8 text-center text-muted-foreground">Загрузка...</div>
          ) : errorTable ? (
            <div className="py-8 text-center text-destructive">Ошибка загрузки данных</div>
          ) : (
            <Table className="table-fixed w-full min-w-[800px]">
              <TableHeader>
                <TableRow className="border-border hover:bg-muted/50">
                  {columns.map((col) => (
                    <TableHead
                      key={col.key}
                      className={cn(
                        "text-muted-foreground px-2 py-1 whitespace-nowrap",
                        col.key === "dateFormatted" ? "text-left" : "text-center"
                      )}
                    >
                      <button
                        onClick={() => handleSort(col.key as SortColumn)}
                        className={cn(
                          "flex items-center gap-0.5 hover:text-foreground transition-colors w-full",
                          col.key === "dateFormatted" ? "justify-start" : "justify-center"
                        )}
                      >
                        {col.label}
                        <span className="flex flex-col">
                          <ChevronUp
                            className={cn(
                              "h-3 w-3 -mb-1",
                              sortColumn === col.key && sortDirection === "asc"
                                ? "text-primary"
                                : "text-muted-foreground/50"
                            )}
                          />
                          <ChevronDown
                            className={cn(
                              "h-3 w-3",
                              sortColumn === col.key && sortDirection === "desc"
                                ? "text-primary"
                                : "text-muted-foreground/50"
                            )}
                          />
                        </span>
                      </button>
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredAndSortedData.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={columns.length} className="text-center text-muted-foreground py-8">
                      Нет данных за выбранный период
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredAndSortedData.map((row, idx) => (
                    <TableRow key={row.date ?? idx} className="border-border hover:bg-muted/50">
                      <TableCell className="font-medium text-foreground px-2 py-1 whitespace-nowrap text-left min-w-0">
                        {row.dateFormatted}
                      </TableCell>
                      <TableCell className="text-foreground px-2 py-1 whitespace-nowrap text-center">{formatNumber(row.orders)}</TableCell>
                      <TableCell className="text-foreground px-2 py-1 whitespace-nowrap text-center">{formatNumber(row.buys)}</TableCell>
                      <TableCell className="text-foreground px-2 py-1 whitespace-nowrap text-center">{formatNumber(row.returns)}</TableCell>
                      <TableCell className="text-foreground px-2 py-1 whitespace-nowrap text-center">{formatNumber(row.revenue)}</TableCell>
                      <TableCell className="text-foreground px-2 py-1 whitespace-nowrap text-center">{formatNumber(row.commission)}</TableCell>
                      <TableCell className="text-foreground px-2 py-1 whitespace-nowrap text-center">{formatNumber(row.logistics)}</TableCell>
                      <TableCell className="text-foreground px-2 py-1 whitespace-nowrap text-center">{formatNumber(row.storage)}</TableCell>
                      <TableCell className="text-foreground px-2 py-1 whitespace-nowrap text-center">{formatNumber(row.ads)}</TableCell>
                      <TableCell className="text-foreground px-2 py-1 whitespace-nowrap text-center">{formatNumber(row.penalties)}</TableCell>
                      <TableCell className="text-foreground px-2 py-1 whitespace-nowrap text-center">{formatNumber(row.cogs)}</TableCell>
                      <TableCell className="text-foreground px-2 py-1 whitespace-nowrap text-center">{formatNumber(row.taxes)}</TableCell>
                      <TableCell className="text-foreground font-bold px-2 py-1 whitespace-nowrap text-center">{formatNumber(row.profit)}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          )}
        </div>
      </div>
    </div>
  );
}
