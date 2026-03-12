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
import { useLanguage } from "@/contexts/LanguageContext";

const MONTH_KEYS = [
  "monthly.jan", "monthly.feb", "monthly.mar", "monthly.apr", "monthly.may", "monthly.jun",
  "monthly.jul", "monthly.aug", "monthly.sep", "monthly.oct", "monthly.nov", "monthly.dec",
];

type RowFormat = "quantityNoUnit" | "currency";

const ROW_LABEL_KEYS: Record<string, string> = {
  ordersCount: "monthly.totalSold",
  revenue: "monthly.revenue",
  productCost: "monthly.cost",
  uzumCommission: "monthly.commission",
  uzumLogistics: "monthly.logistics",
  uzumStorage: "monthly.storage",
  uzumAds: "monthly.ads",
  uzumFines: "monthly.fines",
  taxes1pct: "monthly.tax",
  extraExpenses: "monthly.extraExpenses",
  profit: "monthly.netProfit",
};

/** Строки таблицы: метрика и способ форматирования (как на Сводке). */
const ROWS: {
  id: keyof MonthlyKpiItem;
  isHighlighted: boolean;
  format: RowFormat;
}[] = [
  { id: "ordersCount", isHighlighted: false, format: "quantityNoUnit" },
  { id: "revenue", isHighlighted: false, format: "currency" },
  { id: "productCost", isHighlighted: false, format: "currency" },
  { id: "uzumCommission", isHighlighted: false, format: "currency" },
  { id: "uzumLogistics", isHighlighted: false, format: "currency" },
  { id: "uzumStorage", isHighlighted: false, format: "currency" },
  { id: "uzumAds", isHighlighted: false, format: "currency" },
  { id: "uzumFines", isHighlighted: false, format: "currency" },
  { id: "taxes1pct", isHighlighted: false, format: "currency" },
  { id: "extraExpenses", isHighlighted: false, format: "currency" },
  { id: "profit", isHighlighted: true, format: "currency" },
];

interface MonthlyTableProps {
  /** Год для отображения (обычно год последней даты в выгрузке — fact_sales «Дата создания»). */
  year: number;
  /** Магазин (seller-storage), как на Сводке. */
  shop?: string | null;
  /** Пользовательский процент налога (из вкладки Сводка). Если задан, Налог и Прибыль пересчитываются. */
  taxPercent?: number;
  /** Необязательный переключатель года, рендерится под заголовком. */
  yearSwitcher?: React.ReactNode;
}

export function MonthlyTable({ year, shop = null, taxPercent, yearSwitcher }: MonthlyTableProps) {
  const { t } = useLanguage();
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
        <h3 className="text-lg font-semibold text-foreground">{t('monthly.title')}</h3>
        {yearSwitcher ? (
          <div className="mt-1">
            {yearSwitcher}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground mt-1">
            {year} {t('monthly.year')}
          </p>
        )}
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
          <Table className="table-fixed border-collapse min-w-[1400px] [&_th]:border-r [&_td]:border-r [&_th:last-child]:border-r-0 [&_td:last-child]:border-r-0 [&_th:first-child]:border-border [&_td:first-child]:border-border [&_th:not(:first-child)]:border-border/50 [&_td:not(:first-child)]:border-border/50">
            <TableHeader>
              <TableRow className="bg-violet-50/80 dark:bg-violet-950/30 border-border">
                <TableHead className="w-[140px] min-w-[140px] max-w-[140px] font-semibold text-foreground sticky left-0 bg-violet-50/80 dark:bg-violet-950/30 z-10 border-r border-border">
                  {t('monthly.indicator')}
                </TableHead>
                {MONTH_KEYS.map((key, index) => (
                  <TableHead
                    key={index}
                    className="text-center min-w-[100px] font-medium text-foreground bg-violet-50/80 dark:bg-violet-950/30 border-r border-border/50"
                  >
                    {t(key)}
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
                    {t(ROW_LABEL_KEYS[row.id] ?? row.id)}
                  </TableCell>
                  {MONTH_KEYS.map((_, monthIndex) => {
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
