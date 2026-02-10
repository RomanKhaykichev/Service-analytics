import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { useMonthlyKpi, type MonthlyKpiItem } from "@/hooks/useMonthlyKpi";
import { formatCurrency, formatNumber } from "@/lib/formatters";

const MONTH_LABELS = [
  "Янв", "Фев", "Мар", "Апр", "Май", "Июн",
  "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек",
];

type RowFormat = "quantityNoUnit" | "currency";

/** Строки таблицы: метрика и способ форматирования (как на Сводке). */
const ROWS: {
  id: keyof MonthlyKpiItem;
  label: string;
  labelLine2?: string;
  isHighlighted: boolean;
  format: RowFormat;
}[] = [
  { id: "ordersCount", label: "Всего продано", isHighlighted: false, format: "quantityNoUnit" },
  { id: "revenue", label: "Выручка", isHighlighted: false, format: "currency" },
  { id: "productCost", label: "Себестоимость", isHighlighted: false, format: "currency" },
  { id: "uzumCommission", label: "Комиссия", isHighlighted: false, format: "currency" },
  { id: "uzumLogistics", label: "Логистика", isHighlighted: false, format: "currency" },
  { id: "uzumStorage", label: "Хранение", isHighlighted: false, format: "currency" },
  { id: "uzumAds", label: "Реклама", isHighlighted: false, format: "currency" },
  { id: "uzumFines", label: "Штрафы", isHighlighted: false, format: "currency" },
  { id: "taxes1pct", label: "Налог", isHighlighted: false, format: "currency" },
  { id: "extraExpenses", label: "Доп. расходы", isHighlighted: false, format: "currency" },
  { id: "profit", label: "ЧИСТАЯ ПРИБЫЛЬ", isHighlighted: true, format: "currency" },
];

interface MonthlyTableProps {
  /** Год для отображения (обычно год последней даты в выгрузке — fact_sales «Дата создания»). */
  year: number;
  /** Магазин (seller-storage), как на Сводке. */
  shop?: string | null;
  /** Пользовательский процент налога (из вкладки Сводка). Если задан, Налог и Прибыль пересчитываются. */
  taxPercent?: number;
}

export function MonthlyTable({ year, shop = null, taxPercent }: MonthlyTableProps) {
  const { monthly, loading, error } = useMonthlyKpi(year, shop ?? undefined);

  const getDisplayValue = (rowId: keyof MonthlyKpiItem, item: MonthlyKpiItem): number | undefined => {
    if (taxPercent != null) {
      if (rowId === "taxes1pct") return (item.revenue ?? 0) * (taxPercent / 100);
      if (rowId === "profit")
        return (item.profit ?? 0) + (item.taxes1pct ?? 0) - (item.revenue ?? 0) * (taxPercent / 100);
    }
    const value = item[rowId];
    return value != null && value !== undefined ? value : undefined;
  };

  const formatValue = (rowId: keyof MonthlyKpiItem, monthIndex: number, format: RowFormat): string => {
    if (!monthly || monthIndex >= monthly.length) return "—";
    const item = monthly[monthIndex];
    const value = getDisplayValue(rowId, item);
    if (value == null || value === undefined) return "—";
    if (format === "quantityNoUnit") return formatNumber(value);
    return formatCurrency(value);
  };

  return (
    <div className="bg-card rounded-xl border border-border overflow-hidden">
      <div className="p-4 border-b border-border">
        <h3 className="text-lg font-semibold text-foreground">Финансовые показатели по месяцам</h3>
        <p className="text-sm text-muted-foreground mt-1">{year} год</p>
      </div>
      <div className="overflow-x-auto">
        {loading ? (
          <div className="p-6">
            <Skeleton className="h-8 w-full mb-2" />
            <Skeleton className="h-8 w-full mb-2" />
            <Skeleton className="h-8 w-full mb-2" />
            <Skeleton className="h-8 w-full" />
          </div>
        ) : error ? (
          <div className="p-6 text-destructive text-sm">{error}</div>
        ) : (
          <Table className="table-fixed border-collapse [&_th]:border-r [&_td]:border-r [&_th:last-child]:border-r-0 [&_td:last-child]:border-r-0 [&_th:first-child]:border-border [&_td:first-child]:border-border [&_th:not(:first-child)]:border-border/50 [&_td:not(:first-child)]:border-border/50">
            <TableHeader>
              <TableRow className="bg-violet-50/80 dark:bg-violet-950/30 border-border">
                <TableHead className="w-[140px] min-w-[140px] max-w-[140px] font-semibold text-foreground sticky left-0 bg-violet-50/80 dark:bg-violet-950/30 z-10 border-r border-border">
                  Показатель
                </TableHead>
                {MONTH_LABELS.map((month, index) => (
                  <TableHead
                    key={index}
                    className="text-center min-w-[100px] font-medium text-foreground bg-violet-50/80 dark:bg-violet-950/30 border-r border-border/50"
                  >
                    {month}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {ROWS.map((row) => (
                <TableRow
                  key={row.id}
                  className={`group ${row.isHighlighted ? "bg-primary/10 font-semibold" : ""}`}
                >
                  <TableCell
                    className={`sticky left-0 z-10 w-[140px] min-w-[140px] max-w-[140px] border-r border-border transition-colors ${
                      row.isHighlighted
                        ? "bg-primary/10 text-primary font-bold group-hover:bg-muted/50"
                        : "bg-card font-medium text-foreground group-hover:bg-muted/50"
                    }`}
                  >
                    {row.label}
                  </TableCell>
                  {MONTH_LABELS.map((_, monthIndex) => {
                    const value = formatValue(row.id, monthIndex, row.format);
                    const hasData = value !== "—";
                    return (
                      <TableCell
                        key={monthIndex}
                        className={`text-center whitespace-nowrap border-r border-border/50 ${
                          row.isHighlighted
                            ? "text-primary font-bold"
                            : hasData
                              ? "text-foreground"
                              : "text-muted-foreground"
                        }`}
                      >
                        {value}
                      </TableCell>
                    );
                  })}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
    </div>
  );
}
