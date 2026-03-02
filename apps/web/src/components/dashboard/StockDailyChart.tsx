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
import { useLanguage } from "@/contexts/LanguageContext";

interface StockDailyChartProps {
  points?: Array<{
    date: string;
    orders?: number | null;
    stock: number | null;
  }>;
}

export function StockDailyChart({ points }: StockDailyChartProps) {
  const { t } = useLanguage();
  const [hiddenLines, setHiddenLines] = useState<Set<string>>(new Set());

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
      orders: Number(p.orders ?? 0),
      stock: Number(p.stock ?? 0),
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
              {entry.dataKey === "orders" && t("stockDaily.orders")}
              {entry.dataKey === "stock" && t("stockDaily.stock")}
            </span>
          </button>
        ))}
      </div>
    );
  };

  // Show placeholder if no data
  if (data.length === 0) {
    return (
      <div className="bg-card rounded-xl p-5 border border-border shadow-sm">
        <h3 className="font-semibold text-foreground mb-4">
          {t("stockDaily.title")}
        </h3>
        <div className="h-72 flex items-center justify-center">
          <p className="text-muted-foreground">
            {t("stockDaily.noData")}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-card rounded-xl p-5 border border-border shadow-sm">
      <h3 className="font-semibold text-foreground mb-4">
        {t("stockDaily.title")}
      </h3>
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
              yAxisId="orders"
              domain={[0, 48]}
              ticks={[0, 6, 12, 18, 24, 30, 36, 42, 48]}
              interval={0}
              allowDecimals={false}
              tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
              axisLine={{ stroke: "hsl(var(--border))" }}
              label={{
                value: t("chart.ordersPcs"),
                angle: -90,
                position: "insideLeft",
                style: { fill: "hsl(var(--muted-foreground))", fontSize: 11 },
              }}
            />
            <YAxis
              yAxisId="stock"
              orientation="right"
              tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
              axisLine={{ stroke: "hsl(var(--border))" }}
              label={{
                value: t("stockDaily.stockAxis"),
                angle: 90,
                position: "insideRight",
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
                if (name === "orders") return [value, t("stockDaily.orders")];
                if (name === "stock") {
                  const piecesLabel = t("common.pieces");
                  return [`${value.toLocaleString("ru-RU")} ${piecesLabel}`, t("stockDaily.stock")];
                }
                return [value, name];
              }}
            />
            <Legend content={renderLegend} />
            <Line
              yAxisId="orders"
              type="monotone"
              dataKey="orders"
              stroke="hsl(var(--chart-4))"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              hide={hiddenLines.has("orders")}
            />
            <Line
              yAxisId="stock"
              type="monotone"
              dataKey="stock"
              stroke="hsl(var(--warning))"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              hide={hiddenLines.has("stock")}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

