import { useState } from "react";
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
import { formatCurrency } from "@/lib/formatters";

interface UzumServicesChartProps {
  points?: Array<{
    date: string;
    storage?: number | null;
    ads?: number | null;
    fines?: number | null;
    commission?: number | null;
    logistics?: number | null;
  }>;
  loading?: boolean;
  error?: string | null;
}

export function UzumServicesChart({ points, loading, error }: UzumServicesChartProps) {
  const [hiddenLines, setHiddenLines] = useState<Set<string>>(new Set());

  // Format value in thousands (75000 -> 75 or 75.5) - for Y axis
  const formatThousands = (value: number): string => {
    const thousands = value / 1000;
    // If whole number, show without decimals; otherwise show 1 decimal place
    if (thousands % 1 === 0) {
      return thousands.toString();
    }
    return thousands.toFixed(1);
  };

  // Format full value in sum with thousand separators (51200 -> "51 200 сум")
  const formatFullSum = (value: number): string => {
    const rounded = Math.round(value);
    return `${rounded.toLocaleString("ru-RU")} сум`;
  };

  // Normalize points: convert YYYY-MM-DD to DD.MM format and ensure numbers
  const data = (points ?? []).map((p) => {
    const dateStr = p.date;
    let formattedDate = dateStr;
    // If date is in YYYY-MM-DD format, convert to DD.MM
    if (dateStr.includes("-") && dateStr.length === 10) {
      const [year, month, day] = dateStr.split("-");
      formattedDate = `${day}.${month}`;
    }
    return {
      date: formattedDate,
      storage: Number(p.storage ?? 0),
      ads: Number(p.ads ?? 0),
      fines: Number(p.fines ?? 0),
      commission: Number(p.commission ?? 0),
      logistics: Number(p.logistics ?? 0),
    };
  });

  const handleLegendClick = (dataKey: string) => {
    setHiddenLines((prev) => {
      const next = new Set(prev);
      if (next.has(dataKey)) {
        next.delete(dataKey);
      } else {
        next.add(dataKey);
      }
      return next;
    });
  };

  const renderLegend = (props: any) => {
    const { payload } = props;
    return (
      <div className="flex justify-center gap-4 mt-2">
        {payload.map((entry: any) => (
          <button
            key={entry.dataKey}
            onClick={() => handleLegendClick(entry.dataKey)}
            className={`flex items-center gap-2 px-2 py-1 rounded transition-opacity ${
              hiddenLines.has(entry.dataKey) ? "opacity-40" : "opacity-100"
            }`}
          >
            <span
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-xs text-muted-foreground">
              {entry.dataKey === "storage" && "Хранение"}
              {entry.dataKey === "ads" && "Реклама"}
              {entry.dataKey === "fines" && "Штрафы"}
            </span>
          </button>
        ))}
      </div>
    );
  };

  // Show error state
  if (error) {
    return (
      <div className="bg-card rounded-xl p-5 border border-border shadow-sm">
        <h3 className="font-semibold text-foreground mb-4">Услуги UZUM</h3>
        <div className="h-72 flex items-center justify-center">
          <p className="text-muted-foreground">Не удалось загрузить данные</p>
        </div>
      </div>
    );
  }

  // Show placeholder if no data
  if (!loading && data.length === 0) {
    return (
      <div className="bg-card rounded-xl p-5 border border-border shadow-sm">
        <h3 className="font-semibold text-foreground mb-4">Услуги UZUM</h3>
        <div className="h-72 flex items-center justify-center">
          <p className="text-muted-foreground">Нет данных за выбранный период</p>
        </div>
      </div>
    );
  }

  // Show loading state
  if (loading) {
    return (
      <div className="bg-card rounded-xl p-5 border border-border shadow-sm">
        <h3 className="font-semibold text-foreground mb-4">Услуги UZUM</h3>
        <div className="h-72 flex items-center justify-center">
          <p className="text-muted-foreground">Загрузка...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-card rounded-xl p-5 border border-border shadow-sm">
      <h3 className="font-semibold text-foreground mb-4">Услуги UZUM</h3>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis
              dataKey="date"
              tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
              axisLine={{ stroke: "hsl(var(--border))" }}
            />
            <YAxis
              tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
              axisLine={{ stroke: "hsl(var(--border))" }}
              tickFormatter={(value) => formatThousands(value)}
              label={{
                value: "Затраты, тыс сум",
                angle: -90,
                position: "insideLeft",
                style: { fill: "hsl(var(--muted-foreground))", fontSize: 11 },
              }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "8px",
              }}
              formatter={(value: number, name: string) => {
                const formattedValue = formatFullSum(value);
                if (name === "storage") return [formattedValue, "Хранение"];
                if (name === "ads") return [formattedValue, "Реклама"];
                if (name === "fines") return [formattedValue, "Штрафы"];
                return [formattedValue, name];
              }}
            />
            <Legend content={renderLegend} />
            <Line
              type="monotone"
              dataKey="storage"
              stroke="hsl(var(--chart-1))"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              hide={hiddenLines.has("storage")}
            />
            <Line
              type="monotone"
              dataKey="ads"
              stroke="hsl(var(--chart-2))"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              hide={hiddenLines.has("ads")}
            />
            <Line
              type="monotone"
              dataKey="fines"
              stroke="hsl(var(--chart-3))"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              hide={hiddenLines.has("fines")}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
