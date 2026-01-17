import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

const data = [
  { date: "01.12", revenue: 420000, orders: 1850, avgCheck: 227 },
  { date: "05.12", revenue: 380000, orders: 1720, avgCheck: 221 },
  { date: "10.12", revenue: 520000, orders: 2100, avgCheck: 248 },
  { date: "15.12", revenue: 480000, orders: 1980, avgCheck: 242 },
  { date: "20.12", revenue: 610000, orders: 2450, avgCheck: 249 },
  { date: "25.12", revenue: 720000, orders: 2890, avgCheck: 249 },
  { date: "27.12", revenue: 680000, orders: 2650, avgCheck: 257 },
];

export function RevenueChart() {
  return (
    <div className="chart-container animate-fade-in">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-semibold text-foreground">Выручка и заказы</h3>
          <p className="text-sm text-muted-foreground">Динамика за период</p>
        </div>
      </div>

      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis 
              dataKey="date" 
              stroke="hsl(var(--muted-foreground))"
              fontSize={12}
            />
            <YAxis 
              yAxisId="left"
              stroke="hsl(var(--muted-foreground))"
              fontSize={12}
              tickFormatter={(v) => `${v / 1000}K`}
            />
            <YAxis 
              yAxisId="right"
              orientation="right"
              stroke="hsl(var(--muted-foreground))"
              fontSize={12}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "8px",
                boxShadow: "var(--shadow-md)",
              }}
              labelStyle={{ color: "hsl(var(--foreground))", fontWeight: 600 }}
              formatter={(value: number, name: string) => [
                name === "revenue" ? `${(value / 1000).toFixed(0)}K сум` : value,
                name === "revenue" ? "Выручка" : "Заказы"
              ]}
            />
            <Legend 
              formatter={(value) => value === "revenue" ? "Выручка" : "Заказы"}
            />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="revenue"
              stroke="hsl(var(--primary))"
              strokeWidth={2}
              dot={{ fill: "hsl(var(--primary))", strokeWidth: 2 }}
              activeDot={{ r: 6 }}
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="orders"
              stroke="hsl(var(--accent))"
              strokeWidth={2}
              dot={{ fill: "hsl(var(--accent))", strokeWidth: 2 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
