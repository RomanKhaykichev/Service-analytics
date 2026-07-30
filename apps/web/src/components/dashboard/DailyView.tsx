import { useState, useEffect, useMemo } from "react";
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
import { ChevronUp, ChevronDown, Download } from "lucide-react";
import { cn } from "@/lib/utils";
import { useLanguage } from "@/contexts/LanguageContext";
import { useDailySummary, type DailySummaryGranularity } from "@/hooks/useDailySummary";
import { format, addDays } from "date-fns";
import * as XLSX from "xlsx";
import { toast } from "sonner";
import { getAlignedChartDomains } from "@/lib/alignedChartDomains";

interface DailyViewProps {
  /** Группировка графика: day | week | month — только из селекта "По дням/По неделям/По месяцам" в шапке */
  viewMode?: string;
  dateFrom: string;
  dateTo: string;
  shopId?: string | null;
  /** Shop name (string) from seller-storage for filtering by barcode */
  shop?: string | null;
  /** Пользовательский процент налога (из вкладки Сводка), например 1 = 1% */
  taxPercent?: number;
  /** Пресет видимых серий на графике (например, только хранение из инсайтов) */
  seriesPreset?: "default" | "storage-only";
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

const CHART_SERIES_KEYS: { key: string; labelKey: string; color: string; axis: "count" | "money" }[] = [
  { key: "orders", labelKey: "daily.orders", color: SERIES_COLORS.orders, axis: "count" },
  { key: "returns", labelKey: "daily.returns", color: SERIES_COLORS.returns, axis: "count" },
  { key: "revenue", labelKey: "daily.revenue", color: SERIES_COLORS.revenue, axis: "money" },
  { key: "logistics", labelKey: "daily.logistics", color: SERIES_COLORS.logistics, axis: "money" },
  { key: "ads", labelKey: "daily.ads", color: SERIES_COLORS.ads, axis: "money" },
  { key: "storage", labelKey: "daily.storage", color: SERIES_COLORS.storage, axis: "money" },
  { key: "taxes", labelKey: "daily.tax", color: SERIES_COLORS.taxes, axis: "money" },
  { key: "profit", labelKey: "daily.profitNet", color: SERIES_COLORS.profit, axis: "money" },
];

function formatCountTick(value: number): string {
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  return abs >= 1000 ? `${sign}${(abs / 1000).toFixed(0)}k` : String(value);
}

function formatMoneyTick(value: number): string {
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  if (abs >= 1_000_000) return `${sign}${(abs / 1_000_000).toFixed(1)}M`;
  if (abs >= 1000) return `${sign}${(abs / 1000).toFixed(0)}k`;
  return String(value);
}

const DEFAULT_VISIBLE_SERIES: Record<string, boolean> = {
  orders: true,
  returns: false,
  revenue: true,
  logistics: false,
  ads: false,
  storage: false,
  taxes: false,
  profit: true,
};

const STORAGE_ONLY_VISIBLE_SERIES: Record<string, boolean> = {
  orders: false,
  returns: false,
  revenue: false,
  logistics: false,
  ads: false,
  storage: true,
  taxes: false,
  profit: false,
};

type SortDirection = "asc" | "desc" | null;
type SortColumn = string | null;

function formatChartDateLabel(dateISO: string, granularity: DailySummaryGranularity): string {
  const d = new Date(dateISO);
  if (granularity === "day") return format(d, "dd.MM");
  if (granularity === "week") {
    const end = addDays(d, 6);
    return `${format(d, "dd.MM")}–${format(end, "dd.MM")}`;
  }
  return format(d, "MM.yyyy");
}

export function DailyView({
  viewMode = "day",
  dateFrom,
  dateTo,
  shopId = null,
  shop = null,
  taxPercent = 1,
  seriesPreset = "default",
}: DailyViewProps) {
  const { t, language } = useLanguage();
  const isUz = language === "uz";
  const CHART_SERIES = CHART_SERIES_KEYS.map((s) => ({ ...s, label: t(s.labelKey) }));
  const columns = [
    { key: "dateFormatted", label: t('daily.date') },
    { key: "orders", label: t('daily.orders') },
    { key: "buys", label: t('daily.buys') },
    { key: "returns", label: t('daily.returns') },
    { key: "revenue", label: t('daily.revenue') },
    { key: "commission", label: t('daily.commission') },
    { key: "logistics", label: t('daily.logistics') },
    { key: "storage", label: t('daily.storage') },
    { key: "ads", label: t('daily.ads') },
    { key: "penalties", label: t('daily.penalties') },
    { key: "cogs", label: t('daily.cogs') },
    { key: "taxes", label: t('daily.tax') },
    { key: "profit", label: t('daily.profitNet') },
  ];
  // Гранулярность графика берётся из селекта "По дням/По неделям/По месяцам" (viewMode из SummaryFilters)
  const timeGrouping: DailySummaryGranularity = (viewMode === "week" || viewMode === "month" ? viewMode : "day");
  // График: date_from/date_to + granularity (group_by на бэкенде)
  const { data: chartSummaryData, isLoading: loadingChart, error: errorChart } = useDailySummary({
    dateFrom,
    dateTo,
    shopId: null,
    shop,
    granularity: timeGrouping,
  });
  // Таблица: date_from/date_to + магазин, всегда по дням (без группировки)
  const { data: dailySummaryData, isLoading: loadingTable, error: errorTable } = useDailySummary({ dateFrom, dateTo, shopId, shop });

  // Данные графика: поля для 8 серий + подпись оси X по гранулярности
  const chartData = useMemo(() => {
    if (!chartSummaryData?.points?.length) return [];
    return chartSummaryData.points.map((p) => {
      const revenue = p.revenue ?? 0;
      const commission = p.commission ?? 0;
      const logistics = p.logistics ?? 0;
      const storage = p.storage ?? 0;
      const ads = p.ads ?? 0;
      const penalties = p.penalties ?? 0;
      const cogs = p.cogs ?? 0;

      const adjustedTaxes = Math.round(revenue * (taxPercent / 100));
      const adjustedProfit = Math.round(
        revenue -
          commission -
          logistics -
          storage -
          ads -
          penalties -
          cogs -
          adjustedTaxes
      );

      return {
        date: formatChartDateLabel(p.date, timeGrouping),
        dateISO: p.date,
        orders: p.orders,
        returns: p.returns,
        revenue,
        logistics,
        ads,
        storage,
        taxes: adjustedTaxes,
        profit: adjustedProfit,
      };
    });
  }, [chartSummaryData?.points, timeGrouping, taxPercent]);

  // По умолчанию видны: Заказы, Выручка, Прибыль
  const [visibleSeries, setVisibleSeries] = useState<Record<string, boolean>>(() =>
    seriesPreset === "storage-only" ? STORAGE_ONLY_VISIBLE_SERIES : DEFAULT_VISIBLE_SERIES,
  );

  useEffect(() => {
    if (seriesPreset === "storage-only") {
      setVisibleSeries(STORAGE_ONLY_VISIBLE_SERIES);
    }
  }, [seriesPreset]);
  const toggleSeries = (key: string) => {
    setVisibleSeries((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  // Scale follows only the lines that are actually drawn right now.
  const visibleCountKeys = useMemo(
    () =>
      CHART_SERIES_KEYS.filter((series) => series.axis === "count" && visibleSeries[series.key]).map(
        (series) => series.key,
      ),
    [visibleSeries],
  );
  const visibleMoneyKeys = useMemo(
    () =>
      CHART_SERIES_KEYS.filter((series) => series.axis === "money" && visibleSeries[series.key]).map(
        (series) => series.key,
      ),
    [visibleSeries],
  );
  const yDomains = useMemo(
    () => getAlignedChartDomains(chartData, visibleCountKeys, visibleMoneyKeys),
    [chartData, visibleCountKeys, visibleMoneyKeys],
  );

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
    return dailySummaryData.points.map((p) => {
      const revenue = p.revenue ?? 0;
      const commission = p.commission ?? 0;
      const logistics = p.logistics ?? 0;
      const storage = p.storage ?? 0;
      const ads = p.ads ?? 0;
      const penalties = p.penalties ?? 0;
      const cogs = p.cogs ?? 0;

      const adjustedTaxes = Math.round(revenue * (taxPercent / 100));
      const adjustedProfit = Math.round(
        revenue -
          commission -
          logistics -
          storage -
          ads -
          penalties -
          cogs -
          adjustedTaxes
      );

      return {
        date: p.date,
        dateFormatted: format(new Date(p.date), "dd.MM.yyyy"),
        orders: p.orders,
        buys: p.buys,
        returns: p.returns,
        revenue,
        commission,
        logistics,
        storage,
        ads,
        penalties,
        cogs,
        taxes: adjustedTaxes,
        profit: adjustedProfit,
      };
    });
  }, [dailySummaryData?.points, taxPercent]);

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

  const metricColumns = columns.filter((col) => col.key !== "dateFormatted");

  const handleExportXLSX = () => {
    try {
      if (!tableRows.length) {
        toast.error(t('daily.noDataPeriod'));
        return;
      }
      const rows = tableRows.map((row) => ({
        [t('daily.date')]: row.dateFormatted,
        [t('daily.orders')]: row.orders ?? "",
        [t('daily.buys')]: row.buys ?? "",
        [t('daily.returns')]: row.returns ?? "",
        [t('daily.revenue')]: row.revenue ?? "",
        [t('daily.commission')]: row.commission ?? "",
        [t('daily.logistics')]: row.logistics ?? "",
        [t('daily.storage')]: row.storage ?? "",
        [t('daily.ads')]: row.ads ?? "",
        [t('daily.penalties')]: row.penalties ?? "",
        [t('daily.cogs')]: row.cogs ?? "",
        [t('daily.tax')]: row.taxes ?? "",
        [t('daily.profitNet')]: row.profit ?? "",
      }));
      const worksheet = XLSX.utils.json_to_sheet(rows);
      const workbook = XLSX.utils.book_new();
      const sheetNameRaw = t('daily.dataByDay');
      const sheetName = sheetNameRaw.length > 31 ? sheetNameRaw.slice(0, 31) : sheetNameRaw;
      XLSX.utils.book_append_sheet(workbook, worksheet, sheetName);
      const dateStr = new Date().toISOString().split("T")[0];
      const fileName = isUz ? `kunlik_ma\'lumotlar_${dateStr}.xlsx` : `данные_по_дням_${dateStr}.xlsx`;
      XLSX.writeFile(workbook, fileName);
      toast.success(t('daily.exportedRows').replace('{0}', String(rows.length)));
    } catch (err) {
      console.error("Daily export error:", err);
      toast.error(t('daily.exportError'));
    }
  };

  const renderSortButton = (col: { key: string; label: string }, align: "left" | "center" = "center") => (
    <button
      type="button"
      onClick={() => handleSort(col.key as SortColumn)}
      className={cn(
        "flex items-center gap-0.5 hover:text-foreground transition-colors w-full min-w-0",
        align === "left" ? "justify-start" : "justify-center"
      )}
    >
      <span
        className={cn(
          "leading-tight whitespace-normal break-words",
          align === "left" ? "text-left" : "text-center"
        )}
      >
        {col.label}
      </span>
      <span className="flex flex-col shrink-0">
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
  );

  return (
    <div className="w-full min-w-0 space-y-6">
      {/* График заказов и продаж: 8 метрик (все Line), кнопки выбора метрик, переключатель гранулярности — overlay слева снизу */}
      <div className="bg-card rounded-xl p-3 sm:p-5 border border-border shadow-sm min-w-0">
        <div className="flex items-center gap-3 flex-wrap mb-4">
          <h3 className="font-semibold text-foreground">{t('daily.chartTitle')}</h3>
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

        <div className="relative h-64 sm:h-80 min-w-0">
          {loadingChart ? (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              {t('daily.loading')}
            </div>
          ) : errorChart ? (
            <div className="flex items-center justify-center h-full text-destructive">
              {t('daily.loadError')}
            </div>
          ) : chartData.length === 0 ? (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              {t('daily.noDataPeriod')}
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
                    hide={visibleCountKeys.length === 0}
                    domain={yDomains.left.domain}
                    ticks={yDomains.left.ticks}
                    tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
                    axisLine={{ stroke: "hsl(var(--border))" }}
                    tickFormatter={formatCountTick}
                  />
                  <YAxis
                    yAxisId="money"
                    orientation="right"
                    hide={visibleMoneyKeys.length === 0}
                    domain={yDomains.right.domain}
                    ticks={yDomains.right.ticks}
                    tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
                    axisLine={{ stroke: "hsl(var(--border))" }}
                    tickFormatter={formatMoneyTick}
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
                      const suffix =
                        series?.axis === "money"
                          ? ` ${t("common.sum")}`
                          : series?.axis === "count"
                            ? ` ${t("common.pieces")}`
                            : "";
                      return [formatted + suffix, series?.label ?? name];
                    }}
                  />
                  <Legend
                    wrapperStyle={{ paddingTop: "2px", paddingBottom: 0, marginBottom: 0 }}
                    iconType="circle"
                    iconSize={6}
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
      <div className="bg-card rounded-xl p-3 sm:p-5 border border-border shadow-sm w-full min-w-0">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-4">
          <h3 className="font-semibold text-foreground">{t('daily.dataByDay')}</h3>
          <Button
            variant="outline"
            size="sm"
            onClick={handleExportXLSX}
            disabled={tableRows.length === 0}
            className="w-full sm:w-auto shrink-0"
          >
            <Download className="w-4 h-4 mr-2" />
            {t('daily.exportXLSX')}
          </Button>
        </div>

        {loadingTable ? (
          <div className="py-8 text-center text-muted-foreground">{t('daily.loading')}</div>
        ) : errorTable ? (
          <div className="py-8 text-center text-destructive">{t('daily.loadError')}</div>
        ) : filteredAndSortedData.length === 0 ? (
          <div className="py-8 text-center text-muted-foreground">{t('daily.noDataPeriod')}</div>
        ) : (
          <>
            {/* Mobile: карточки по дням */}
            <div className="md:hidden space-y-3">
              {filteredAndSortedData.map((row, idx) => (
                <div
                  key={row.date ?? idx}
                  className="rounded-lg border border-border bg-background/60 p-3 space-y-3"
                >
                  <div className="font-semibold text-foreground">{row.dateFormatted}</div>
                  <div className="grid grid-cols-2 gap-x-3 gap-y-2 text-xs sm:text-sm">
                    {metricColumns.map((col) => {
                      const value = row[col.key as keyof typeof row];
                      const isProfit = col.key === "profit";
                      return (
                        <div
                          key={col.key}
                          className={cn(
                            "flex flex-col gap-0.5 min-w-0",
                            isProfit && "col-span-2 border-t border-border pt-2 mt-0.5"
                          )}
                        >
                          <span className="text-muted-foreground leading-tight">{col.label}</span>
                          <span
                            className={cn(
                              "tabular-nums text-foreground",
                              isProfit && "font-bold text-base"
                            )}
                          >
                            {typeof value === "number" ? formatNumber(value) : value}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>

            {/* Desktop / tablet: таблица с горизонтальным скроллом */}
            <div
              className={cn(
                "hidden md:block relative data-table w-full min-w-0 max-w-full rounded-lg border border-border",
                (filteredAndSortedData?.length ?? 0) > 15
                  ? "max-h-[min(70vh,32rem)] lg:max-h-[min(78vh,40rem)]"
                  : ""
              )}
            >
              <div
                className={cn(
                  "overflow-auto overscroll-contain touch-pan-x touch-pan-y [scrollbar-gutter:stable]",
                  (filteredAndSortedData?.length ?? 0) > 15 && "max-h-[min(70vh,32rem)] lg:max-h-[min(78vh,40rem)]"
                )}
              >
                <Table
                  wrapperClassName="overflow-visible min-w-0"
                  className="w-max min-w-full caption-bottom text-xs lg:text-sm"
                >
                  <TableHeader>
                    <TableRow className="bg-violet-50/80 dark:bg-violet-950/30 border-border">
                      {columns.map((col, index) => (
                        <TableHead
                          key={col.key}
                          className={cn(
                            "sticky top-0 z-20 text-muted-foreground px-1.5 lg:px-2 py-1.5 border-b border-border",
                            "bg-violet-50/95 dark:bg-violet-950/95 backdrop-blur-sm",
                            "whitespace-normal leading-tight align-bottom",
                            col.key === "dateFormatted" ? "text-left" : "text-center",
                            index === 0 &&
                              "sticky left-0 z-40 border-r border-border min-w-[6.5rem] lg:min-w-[7.5rem]",
                            index > 0 && "min-w-[4.5rem] lg:min-w-[5.5rem]"
                          )}
                        >
                          {renderSortButton(col, col.key === "dateFormatted" ? "left" : "center")}
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredAndSortedData.map((row, idx) => (
                      <TableRow key={row.date ?? idx} className="border-border hover:bg-muted/50">
                        <TableCell className="font-medium text-foreground px-1.5 lg:px-2 py-1.5 whitespace-nowrap text-left sticky left-0 z-10 bg-card border-r border-border min-w-[6.5rem] lg:min-w-[7.5rem]">
                          {row.dateFormatted}
                        </TableCell>
                        {metricColumns.map((col) => {
                          const value = row[col.key as keyof typeof row];
                          const isProfit = col.key === "profit";
                          return (
                            <TableCell
                              key={col.key}
                              className={cn(
                                "text-foreground px-1.5 lg:px-2 py-1.5 whitespace-nowrap text-center tabular-nums",
                                isProfit && "font-bold"
                              )}
                            >
                              {typeof value === "number" ? formatNumber(value) : value}
                            </TableCell>
                          );
                        })}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
