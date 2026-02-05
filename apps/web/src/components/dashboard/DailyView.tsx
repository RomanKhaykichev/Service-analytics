import { useState, useMemo } from "react";
import {
  ComposedChart,
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
import { useDailySummary, type DailySummaryGranularity } from "@/hooks/useDailySummary";
import { format, addDays } from "date-fns";

interface DailyViewProps {
  /** Группировка графика: day | week | month — только из селекта "По дням/По неделям/По месяцам" в шапке */
  viewMode?: string;
  dateFrom: string;
  dateTo: string;
  shopId?: string | null;
  /** Shop name (string) from seller-storage for filtering by barcode */
  shop?: string | null;
}

// 8 метрик на графике: левая ось (шт) — Заказы, Возвраты; правая (сум) — остальные. Все серии — Line.
const SERIES_COLORS: Record<string, string> = {
  orders: "#2563EB",
  returns: "#DC2626",
  revenue: "#F59E0B",
  logistics: "#06B6D4",
  ads: "#EC4899",
  storage: "#64748B",
  taxes: "#A855F7",
  profit: "#7C3AED",
};

const CHART_SERIES = [
  { key: "orders", label: "Заказы", color: SERIES_COLORS.orders, axis: "count" as const },
  { key: "returns", label: "Возвраты", color: SERIES_COLORS.returns, axis: "count" as const },
  { key: "revenue", label: "Выручка", color: SERIES_COLORS.revenue, axis: "money" as const },
  { key: "logistics", label: "Логистика", color: SERIES_COLORS.logistics, axis: "money" as const },
  { key: "ads", label: "Реклама", color: SERIES_COLORS.ads, axis: "money" as const },
  { key: "storage", label: "Хранение", color: SERIES_COLORS.storage, axis: "money" as const },
  { key: "taxes", label: "Налоги", color: SERIES_COLORS.taxes, axis: "money" as const },
  { key: "profit", label: "Прибыль", color: SERIES_COLORS.profit, axis: "money" as const },
];

type SortDirection = "asc" | "desc" | null;
type SortColumn = string | null;

const GRANULARITY_OPTIONS: { value: DailySummaryGranularity; label: string }[] = [
  { value: "day", label: "День" },
  { value: "week", label: "Неделя" },
  { value: "month", label: "Месяц" },
];

function formatChartDateLabel(dateISO: string, granularity: DailySummaryGranularity): string {
  const d = new Date(dateISO);
  if (granularity === "day") return format(d, "dd.MM");
  if (granularity === "week") {
    const end = addDays(d, 6);
    return `${format(d, "dd.MM")}–${format(end, "dd.MM")}`;
  }
  return format(d, "MM.yyyy");
}

export function DailyView({ viewMode = "day", dateFrom, dateTo, shopId = null, shop = null }: DailyViewProps) {
  // Гранулярность графика берётся из селекта "По дням/По неделям/По месяцам" (viewMode из SummaryFilters)
  const timeGrouping: DailySummaryGranularity = (viewMode === "week" || viewMode === "month" ? viewMode : "day");
  // График: date_from/date_to + granularity (group_by на бэкенде)
  const { data: chartSummaryData, isLoading: loadingChart, error: errorChart } = useDailySummary({
    dateFrom,
    dateTo,
    shopId: null,
    shop: null,
    granularity: timeGrouping,
  });
  // Таблица: date_from/date_to + магазин, всегда по дням (без группировки)
  const { data: dailySummaryData, isLoading: loadingTable, error: errorTable } = useDailySummary({ dateFrom, dateTo, shopId, shop });

  // Данные графика: поля для 8 серий + подпись оси X по гранулярности
  const chartData = useMemo(() => {
    if (!chartSummaryData?.points?.length) return [];
    return chartSummaryData.points.map((p) => ({
      date: formatChartDateLabel(p.date, timeGrouping),
      dateISO: p.date,
      orders: p.orders,
      returns: p.returns,
      revenue: p.revenue,
      logistics: p.logistics,
      ads: p.ads,
      storage: p.storage,
      taxes: p.taxes,
      profit: p.profit,
    }));
  }, [chartSummaryData?.points, timeGrouping]);

  // По умолчанию видны: Заказы, Выручка, Прибыль
  const [visibleSeries, setVisibleSeries] = useState<Record<string, boolean>>({
    orders: true,
    returns: false,
    revenue: true,
    logistics: false,
    ads: false,
    storage: false,
    taxes: false,
    profit: true,
  });
  const toggleSeries = (key: string) => {
    setVisibleSeries((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const [sortColumn, setSortColumn] = useState<SortColumn>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);

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
      {/* График заказов и продаж: 8 метрик (все Line), кнопки выбора метрик, переключатель гранулярности — overlay слева снизу */}
      <div className="bg-card rounded-xl p-5 border border-border shadow-sm">
        <div className="flex items-center gap-3 flex-wrap mb-4">
          <h3 className="font-semibold text-foreground">График заказов и продаж</h3>
          <div className="flex items-center gap-2 ml-auto flex-wrap justify-end">
            {CHART_SERIES.map((s) => (
              <Button
                key={s.key}
                variant={visibleSeries[s.key] ? "default" : "outline"}
                size="sm"
                onClick={() => toggleSeries(s.key)}
                className="text-xs"
                style={{
                  backgroundColor: visibleSeries[s.key] ? s.color : undefined,
                  borderColor: s.color,
                  color: visibleSeries[s.key] ? "white" : s.color,
                }}
              >
                {s.label}
              </Button>
            ))}
          </div>
        </div>

        <div className="relative h-80">
          {loadingChart ? (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              Загрузка...
            </div>
          ) : errorChart ? (
            <div className="flex items-center justify-center h-full text-destructive">
              Ошибка загрузки данных
            </div>
          ) : chartData.length === 0 ? (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              Нет данных за выбранный период
            </div>
          ) : (
            <>
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart
                  data={chartData}
                  margin={{ top: 8, right: 8, left: 4, bottom: 16 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
                    axisLine={{ stroke: "hsl(var(--border))" }}
                  />
                  <YAxis
                    yAxisId="count"
                    tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
                    axisLine={{ stroke: "hsl(var(--border))" }}
                    tickFormatter={(v) => (v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v))}
                  />
                  <YAxis
                    yAxisId="money"
                    orientation="right"
                    tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
                    axisLine={{ stroke: "hsl(var(--border))" }}
                    tickFormatter={(v) => (v >= 1_000_000 ? `${(v / 1_000_000).toFixed(1)}M` : v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v))}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                    }}
                    formatter={(value: number, name: string) => {
                      const series = CHART_SERIES.find((s) => s.key === name);
                      const formatted = formatNumber(Number(value));
                      const suffix = series?.axis === "money" ? " сум" : "";
                      return [formatted + suffix, series?.label ?? name];
                    }}
                  />
                  <Legend
                    wrapperStyle={{ paddingTop: "2px", paddingBottom: 0, marginBottom: 0 }}
                    formatter={(value) => CHART_SERIES.find((s) => s.key === value)?.label ?? value}
                  />
                  {CHART_SERIES.filter((s) => visibleSeries[s.key]).map((s) => (
                    <Line
                      key={s.key}
                      type="monotone"
                      dataKey={s.key}
                      name={s.key}
                      stroke={s.color}
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 4 }}
                      yAxisId={s.axis === "count" ? "count" : "money"}
                    />
                  ))}
                </ComposedChart>
              </ResponsiveContainer>
            </>
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
                <TableRow className="bg-violet-50/80 dark:bg-violet-950/30 border-border">
                  {columns.map((col) => (
                    <TableHead
                      key={col.key}
                      className={cn(
                        "text-muted-foreground px-2 py-1 whitespace-nowrap bg-violet-50/80 dark:bg-violet-950/30",
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
