import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { useLanguage } from "@/contexts/LanguageContext";

const data = [
  { name: "Электроника", sales: 4200000, color: "hsl(var(--primary))" },
  { name: "Дом и кухня", sales: 3100000, color: "hsl(var(--accent))" },
  { name: "Красота", sales: 2800000, color: "hsl(var(--warning))" },
  { name: "Одежда", sales: 2300000, color: "hsl(var(--chart-4))" },
];

export function CategoryChart() {
  const { t } = useLanguage();
  return (
    <div className="chart-container animate-fade-in">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-semibold text-foreground">
            {t("categoryChart.title")}
          </h3>
          <p className="text-sm text-muted-foreground">
            {t("categoryChart.subtitle")}
          </p>
        </div>
      </div>

      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ left: 20, right: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
            <XAxis 
              type="number" 
              stroke="hsl(var(--muted-foreground))"
              fontSize={12}
              tickFormatter={(v) => `${v / 1000000}M`}
            />
            <YAxis 
              type="category" 
              dataKey="name"
              stroke="hsl(var(--muted-foreground))"
              fontSize={12}
              width={90}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "8px",
              }}
              formatter={(value: number) => [
                `${(value / 1000000).toFixed(1)}M ${t("common.sum")}`,
                t("categoryChart.tooltipSales"),
              ]}
            />
            <Bar dataKey="sales" radius={[0, 4, 4, 0]}>
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
