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

const data = [
  { date: "01.12", orders: 220, stock: 8500 },
  { date: "02.12", orders: 245, stock: 8200 },
  { date: "03.12", orders: 180, stock: 7900 },
  { date: "04.12", orders: 120, stock: 7600 },
  { date: "05.12", orders: 90, stock: 7400 },
  { date: "06.12", orders: 150, stock: 8100 },
  { date: "07.12", orders: 200, stock: 8800 },
  { date: "08.12", orders: 280, stock: 9200 },
  { date: "09.12", orders: 320, stock: 9800 },
  { date: "10.12", orders: 350, stock: 10500 },
  { date: "11.12", orders: 380, stock: 11200 },
  { date: "12.12", orders: 400, stock: 12500 },
  { date: "13.12", orders: 420, stock: 13161 },
];

export function StockDailyChart() {
  const [hiddenLines, setHiddenLines] = useState<Set<string>>(new Set());

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
              {entry.dataKey === "orders" && "Заказы"}
              {entry.dataKey === "stock" && "Товары на складе"}
            </span>
          </button>
        ))}
      </div>
    );
  };

  return (
    <div className="bg-card rounded-xl p-5 border border-border shadow-sm">
      <h3 className="font-semibold text-foreground mb-4">Складские остатки по дням</h3>
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
              yAxisId="left"
              tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
              axisLine={{ stroke: "hsl(var(--border))" }}
              label={{
                value: "Заказы, шт",
                angle: -90,
                position: "insideLeft",
                style: { fill: "hsl(var(--muted-foreground))", fontSize: 11 },
              }}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
              axisLine={{ stroke: "hsl(var(--border))" }}
              tickFormatter={(value) => `${(value / 1000).toFixed(0)}k`}
              label={{
                value: "Товары на складе, шт",
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
                if (name === "orders") return [value, "Заказы"];
                if (name === "stock") return [`${value.toLocaleString()} шт`, "Товары на складе"];
                return [value, name];
              }}
            />
            <Legend content={renderLegend} />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="orders"
              stroke="hsl(var(--chart-4))"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              hide={hiddenLines.has("orders")}
            />
            <Line
              yAxisId="right"
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
