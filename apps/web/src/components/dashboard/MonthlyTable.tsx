import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const months = [
  "Янв", "Фев", "Мар", "Апр", "Май", "Июн",
  "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"
];

const rows = [
  { id: "soldItems", label: "Всего продано товара, шт", isHighlighted: false },
  { id: "revenue", label: "Выручка", isHighlighted: false },
  { id: "cost", label: "Себестоимость", isHighlighted: false },
  { id: "commission", label: "Комиссия UZUM", isHighlighted: false },
  { id: "logistics", label: "Логистика", isHighlighted: false },
  { id: "storage", label: "Хранение", isHighlighted: false },
  { id: "advertising", label: "Реклама", isHighlighted: false },
  { id: "tax", label: "Налог", isHighlighted: false },
  { id: "other", label: "Прочее", isHighlighted: false },
  { id: "netProfit", label: "ЧИСТАЯ ПРИБЫЛЬ", isHighlighted: true },
];

// Sample data - months with data (0-indexed)
const sampleData: Record<string, Record<number, string>> = {
  soldItems: { 0: "1 245", 1: "1 532", 2: "1 875", 3: "2 110", 4: "1 980" },
  revenue: { 0: "12 450 000", 1: "15 320 000", 2: "18 750 000", 3: "21 100 000", 4: "19 800 000" },
  cost: { 0: "4 980 000", 1: "6 128 000", 2: "7 500 000", 3: "8 440 000", 4: "7 920 000" },
  commission: { 0: "1 868 000", 1: "2 298 000", 2: "2 813 000", 3: "3 165 000", 4: "2 970 000" },
  logistics: { 0: "622 500", 1: "766 000", 2: "937 500", 3: "1 055 000", 4: "990 000" },
  storage: { 0: "124 500", 1: "153 200", 2: "187 500", 3: "211 000", 4: "198 000" },
  advertising: { 0: "500 000", 1: "750 000", 2: "1 000 000", 3: "1 200 000", 4: "800 000" },
  tax: { 0: "498 000", 1: "612 800", 2: "750 000", 3: "844 000", 4: "792 000" },
  other: { 0: "100 000", 1: "120 000", 2: "150 000", 3: "180 000", 4: "160 000" },
  netProfit: { 0: "3 757 000", 1: "4 492 000", 2: "5 412 000", 3: "6 005 000", 4: "5 970 000" },
};

export function MonthlyTable() {
  const formatValue = (rowId: string, monthIndex: number): string => {
    return sampleData[rowId]?.[monthIndex] ?? "—";
  };

  return (
    <div className="bg-card rounded-xl border border-border overflow-hidden">
      <div className="p-4 border-b border-border">
        <h3 className="text-lg font-semibold text-foreground">Финансовые показатели по месяцам</h3>
        <p className="text-sm text-muted-foreground mt-1">2025 год</p>
      </div>
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30">
              <TableHead className="min-w-[160px] font-semibold text-foreground sticky left-0 bg-muted/30 z-10">
                Показатель
              </TableHead>
              {months.map((month, index) => (
                <TableHead 
                  key={index} 
                  className="text-center min-w-[100px] font-medium text-foreground"
                >
                  {month}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow 
                key={row.id}
                className={row.isHighlighted ? "bg-primary/10 font-semibold" : ""}
              >
                <TableCell 
                  className={`sticky left-0 z-10 ${
                    row.isHighlighted 
                      ? "bg-primary/10 text-primary font-bold" 
                      : "bg-card font-medium text-foreground"
                  }`}
                >
                  {row.label}
                </TableCell>
                {months.map((_, monthIndex) => {
                  const value = formatValue(row.id, monthIndex);
                  const hasData = value !== "—";
                  
                  return (
                    <TableCell 
                      key={monthIndex}
                      className={`text-center whitespace-nowrap ${
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
      </div>
    </div>
  );
}
