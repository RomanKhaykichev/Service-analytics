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
import { ChevronUp, ChevronDown, Filter } from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { useOrdersSalesDaily } from "@/hooks/useOrdersSalesDaily";
import { format, startOfWeek, endOfWeek, addDays } from "date-fns";
import { ru } from "date-fns/locale";

interface DailyViewProps {
  viewMode?: string;
  periodCode?: string;
  shopId?: string | null;
  /** Shop name (string) from seller-storage for filtering by barcode */
  shop?: string | null;
}

const tableData = [
  { date: "13.12.2024", orderedQty: 295, purchasedQty: 268, canceledQty: 12, revenue: 5430000, commission: 543000, costPrice: 271500, logistics: 108600, advertising: 81450, taxes: 162900, additionalExpenses: 54300, netProfit: 4207750 },
  { date: "12.12.2024", orderedQty: 278, purchasedQty: 250, canceledQty: 15, revenue: 5060000, commission: 506000, costPrice: 253000, logistics: 101200, advertising: 75900, taxes: 151800, additionalExpenses: 50600, netProfit: 3921500 },
  { date: "11.12.2024", orderedQty: 256, purchasedQty: 228, canceledQty: 18, revenue: 4620000, commission: 462000, costPrice: 231000, logistics: 92400, advertising: 69300, taxes: 138600, additionalExpenses: 46200, netProfit: 3580500 },
  { date: "10.12.2024", orderedQty: 234, purchasedQty: 208, canceledQty: 16, revenue: 4210000, commission: 421000, costPrice: 210500, logistics: 84200, advertising: 63150, taxes: 126300, additionalExpenses: 42100, netProfit: 3262750 },
  { date: "09.12.2024", orderedQty: 210, purchasedQty: 185, canceledQty: 14, revenue: 3750000, commission: 375000, costPrice: 187500, logistics: 75000, advertising: 56250, taxes: 112500, additionalExpenses: 37500, netProfit: 2906250 },
  { date: "08.12.2024", orderedQty: 189, purchasedQty: 165, canceledQty: 11, revenue: 3340000, commission: 334000, costPrice: 167000, logistics: 66800, advertising: 50100, taxes: 100200, additionalExpenses: 33400, netProfit: 2588500 },
  { date: "07.12.2024", orderedQty: 156, purchasedQty: 134, canceledQty: 9, revenue: 2710000, commission: 271000, costPrice: 135500, logistics: 54200, advertising: 40650, taxes: 81300, additionalExpenses: 27100, netProfit: 2100250 },
  { date: "06.12.2024", orderedQty: 112, purchasedQty: 95, canceledQty: 7, revenue: 1920000, commission: 192000, costPrice: 96000, logistics: 38400, advertising: 28800, taxes: 57600, additionalExpenses: 19200, netProfit: 1488000 },
  { date: "05.12.2024", orderedQty: 76, purchasedQty: 62, canceledQty: 3, revenue: 1250000, commission: 125000, costPrice: 62500, logistics: 25000, advertising: 18750, taxes: 37500, additionalExpenses: 12500, netProfit: 968750 },
  { date: "04.12.2024", orderedQty: 98, purchasedQty: 85, canceledQty: 4, revenue: 1720000, commission: 172000, costPrice: 86000, logistics: 34400, advertising: 25800, taxes: 51600, additionalExpenses: 17200, netProfit: 1333000 },
  { date: "03.12.2024", orderedQty: 132, purchasedQty: 108, canceledQty: 6, revenue: 2180000, commission: 218000, costPrice: 109000, logistics: 43600, advertising: 32700, taxes: 65400, additionalExpenses: 21800, netProfit: 1689500 },
  { date: "02.12.2024", orderedQty: 168, purchasedQty: 142, canceledQty: 12, revenue: 2890000, commission: 289000, costPrice: 144500, logistics: 57800, advertising: 43350, taxes: 86700, additionalExpenses: 28900, netProfit: 2239750 },
  { date: "01.12.2024", orderedQty: 145, purchasedQty: 120, canceledQty: 8, revenue: 2450000, commission: 245000, costPrice: 122500, logistics: 49000, advertising: 36750, taxes: 73500, additionalExpenses: 24500, netProfit: 1898750 },
];

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
  const [columnFilters, setColumnFilters] = useState<Record<string, { min: string; max: string }>>({});

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

  const handleColumnFilter = (column: string, type: "min" | "max", value: string) => {
    setColumnFilters((prev) => ({
      ...prev,
      [column]: { ...prev[column], [type]: value },
    }));
  };

  const filteredAndSortedData = [...tableData]
    .filter((row) => {
      return Object.entries(columnFilters).every(([column, filter]) => {
        if (!filter.min && !filter.max) return true;
        const value = row[column as keyof typeof row];
        if (typeof value !== "number") return true;
        if (filter.min && value < Number(filter.min)) return false;
        if (filter.max && value > Number(filter.max)) return false;
        return true;
      });
    })
    .sort((a, b) => {
      if (!sortColumn || !sortDirection) return 0;
      const aVal = a[sortColumn];
      const bVal = b[sortColumn];
      if (typeof aVal === "string" && typeof bVal === "string") {
        return sortDirection === "asc" ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      }
      if (typeof aVal === "number" && typeof bVal === "number") {
        return sortDirection === "asc" ? aVal - bVal : bVal - aVal;
      }
      return 0;
    });

  const formatNumber = (num: number) => num.toLocaleString("ru-RU");

  const columns = [
    { key: "date", label: "Дата" },
    { key: "orderedQty", label: "Заказали, шт" },
    { key: "purchasedQty", label: "Выкупы, шт" },
    { key: "canceledQty", label: "Отмена, шт" },
    { key: "revenue", label: "Выручка" },
    { key: "commission", label: "Комиссия" },
    { key: "costPrice", label: "Себестоимость" },
    { key: "logistics", label: "Логистика" },
    { key: "advertising", label: "Реклама" },
    { key: "taxes", label: "Налоги" },
    { key: "additionalExpenses", label: "Доп. расходы" },
    { key: "netProfit", label: "Чистая прибыль" },
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

      {/* Table Section */}
      <div className="bg-card rounded-xl p-5 border border-border shadow-sm">
        <h3 className="font-semibold text-foreground mb-4">Данные по дням</h3>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="border-border hover:bg-muted/50">
                {columns.map((col) => (
                  <TableHead key={col.key} className="text-muted-foreground">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleSort(col.key as SortColumn)}
                        className="flex items-center gap-1 hover:text-foreground transition-colors"
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
                      {col.key !== "date" && (
                        <Popover>
                          <PopoverTrigger asChild>
                            <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                              <Filter className="h-3 w-3 text-muted-foreground" />
                            </Button>
                          </PopoverTrigger>
                          <PopoverContent className="w-48 bg-card border-border" align="start">
                            <div className="space-y-2">
                              <p className="text-sm font-medium text-foreground">Фильтр по диапазону</p>
                              <Input
                                type="number"
                                placeholder="Мин"
                                value={columnFilters[col.key]?.min || ""}
                                onChange={(e) => handleColumnFilter(col.key, "min", e.target.value)}
                                className="h-8 bg-background border-border"
                              />
                              <Input
                                type="number"
                                placeholder="Макс"
                                value={columnFilters[col.key]?.max || ""}
                                onChange={(e) => handleColumnFilter(col.key, "max", e.target.value)}
                                className="h-8 bg-background border-border"
                              />
                            </div>
                          </PopoverContent>
                        </Popover>
                      )}
                    </div>
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredAndSortedData.map((row, idx) => (
                <TableRow key={idx} className="border-border hover:bg-muted/50">
                  <TableCell className="font-medium text-foreground">{row.date}</TableCell>
                  <TableCell className="text-foreground">{formatNumber(row.orderedQty)}</TableCell>
                  <TableCell className="text-foreground">{formatNumber(row.purchasedQty)}</TableCell>
                  <TableCell className="text-foreground">{formatNumber(row.canceledQty)}</TableCell>
                  <TableCell className="text-foreground">{formatNumber(row.revenue)}</TableCell>
                  <TableCell className="text-foreground">{formatNumber(row.commission)}</TableCell>
                  <TableCell className="text-foreground">{formatNumber(row.costPrice)}</TableCell>
                  <TableCell className="text-foreground">{formatNumber(row.taxes)}</TableCell>
                  <TableCell className="text-foreground">{formatNumber(row.additionalExpenses)}</TableCell>
                  <TableCell className="text-foreground font-bold">{formatNumber(row.netProfit)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}
