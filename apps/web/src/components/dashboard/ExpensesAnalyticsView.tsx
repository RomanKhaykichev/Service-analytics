import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Briefcase, Flame, Info, Package, Truck } from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";
import { useExpensesBreakdown } from "@/hooks/useExpensesBreakdown";
import { formatMillions, formatMoneyNoDecimals } from "@/lib/formatters";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip as UiTooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

interface ExpensesAnalyticsViewProps {
  dateFrom: string;
  dateTo: string;
  shop?: string | null;
}

const SERVICE_COLORS: Record<string, string> = {
  "Буст в топ": "#F97316",
  "Буст заказов": "#EF4444",
  Хранение: "#06B6D4",
  "Хранение собранного возврата": "#22D3EE",
  "Закреплённый отзыв": "#16A34A",
  Утилизация: "#84CC16",
  "Утилизация товара": "#84CC16",
  Логистика: "#7C3AED",
  Штраф: "#DC2626",
  Реклама: "#F59E0B",
  Прочее: "#94A3B8",
};

const FALLBACK_PALETTE = [
  "#7C3AED",
  "#F97316",
  "#EF4444",
  "#06B6D4",
  "#22D3EE",
  "#16A34A",
  "#84CC16",
  "#A855F7",
  "#F43F5E",
  "#0EA5E9",
];

const MONTH_DATIVE_RU = [
  "",
  "январю",
  "февралю",
  "марту",
  "апрелю",
  "маю",
  "июню",
  "июлю",
  "августу",
  "сентябрю",
  "октябрю",
  "ноябрю",
  "декабрю",
];

const MONTH_DATIVE_UZ = [
  "",
  "yanvar",
  "fevral",
  "mart",
  "aprel",
  "may",
  "iyun",
  "iyul",
  "avgust",
  "sentabr",
  "oktabr",
  "noyabr",
  "dekabr",
];

function colorForService(name: string, index: number): string {
  if (SERVICE_COLORS[name]) return SERVICE_COLORS[name];
  const lower = name.toLowerCase();
  for (const [key, color] of Object.entries(SERVICE_COLORS)) {
    if (lower.includes(key.toLowerCase())) return color;
  }
  return FALLBACK_PALETTE[index % FALLBACK_PALETTE.length];
}

function TrendBadge({
  changePct,
  compareLabel,
  tone,
}: {
  changePct: number | null | undefined;
  compareLabel: string;
  tone: "purple" | "orange" | "cyan";
}) {
  if (changePct === null || changePct === undefined) {
    return <span className="text-xs text-muted-foreground">—</span>;
  }
  const up = changePct >= 0;
  const toneClass =
    tone === "purple"
      ? "bg-violet-100 text-violet-700 dark:bg-violet-950/50 dark:text-violet-300"
      : tone === "orange"
        ? "bg-orange-100 text-orange-700 dark:bg-orange-950/40 dark:text-orange-300"
        : "bg-cyan-100 text-cyan-700 dark:bg-cyan-950/40 dark:text-cyan-300";

  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium", toneClass)}>
      <span aria-hidden>{up ? "↑" : "↓"}</span>
      <span>
        {up ? "" : "−"}
        {Math.abs(changePct).toFixed(1)}% {compareLabel}
      </span>
    </span>
  );
}

function KpiCard({
  title,
  amount,
  changePct,
  compareLabel,
  icon: Icon,
  iconWrapClass,
  iconClass,
  tone,
}: {
  title: string;
  amount: number;
  changePct: number | null | undefined;
  compareLabel: string;
  icon: typeof Briefcase;
  iconWrapClass: string;
  iconClass: string;
  tone: "purple" | "orange" | "cyan";
}) {
  return (
    <div className="bg-card rounded-xl border border-border shadow-sm p-5 animate-fade-in">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm text-muted-foreground">{title}</p>
        <div className={cn("w-9 h-9 rounded-lg flex items-center justify-center shrink-0", iconWrapClass)}>
          <Icon className={cn("w-5 h-5", iconClass)} />
        </div>
      </div>
      <p className="mt-3 text-2xl font-bold tracking-tight text-foreground">
        {formatMoneyNoDecimals(amount, "сум")}
      </p>
      <div className="mt-3">
        <TrendBadge changePct={changePct} compareLabel={compareLabel} tone={tone} />
      </div>
    </div>
  );
}

function ChartTitle({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex items-center gap-1.5 mb-4">
      <h3 className="text-base font-semibold text-foreground">{title}</h3>
      {hint && (
        <UiTooltip>
          <TooltipTrigger asChild>
            <button type="button" className="text-muted-foreground hover:text-foreground" aria-label={hint}>
              <Info className="w-4 h-4" />
            </button>
          </TooltipTrigger>
          <TooltipContent className="max-w-xs">{hint}</TooltipContent>
        </UiTooltip>
      )}
    </div>
  );
}

export function ExpensesAnalyticsView({ dateFrom, dateTo, shop }: ExpensesAnalyticsViewProps) {
  const { t, language } = useLanguage();
  const { summary, services, weekly, loading, error } = useExpensesBreakdown({
    dateFrom,
    dateTo,
    shop: shop && shop !== "all" ? shop : null,
  });

  const compareLabel = useMemo(() => {
    const month = summary?.compare_month;
    const year = summary?.compare_year;
    if (!month || !year) return "";
    if (language === "uz") {
      return `${MONTH_DATIVE_UZ[month]} ${year} ga`;
    }
    return `к ${MONTH_DATIVE_RU[month]} ${year}`;
  }, [summary?.compare_month, summary?.compare_year, language]);

  const colorByName = useMemo(() => {
    const map: Record<string, string> = {};
    services.forEach((s, i) => {
      map[s.name] = colorForService(s.name, i);
    });
    return map;
  }, [services]);

  const barData = useMemo(
    () =>
      services
        .filter((s) => Math.abs(s.amount) > 0.009)
        .map((s) => ({
          name: s.name,
          amount: s.amount,
          share: s.share_pct,
          fill: colorByName[s.name],
        })),
    [services, colorByName],
  );

  const donutData = useMemo(
    () =>
      services
        .filter((s) => s.amount > 0)
        .map((s) => ({
          name: s.name,
          value: s.amount,
          share: s.share_pct,
          fill: colorByName[s.name],
        })),
    [services, colorByName],
  );

  const chartTotal = useMemo(
    () => services.reduce((sum, s) => sum + (s.amount > 0 ? s.amount : 0), 0),
    [services],
  );

  const weeklyChartData = useMemo(() => {
    return weekly.map((w) => {
      const row: Record<string, string | number> = {
        label: w.label,
        total: w.total,
      };
      for (const part of w.parts) {
        row[part.name] = part.amount;
      }
      return row;
    });
  }, [weekly]);

  const stackKeys = useMemo(
    () => services.filter((s) => Math.abs(s.amount) > 0.009).map((s) => s.name),
    [services],
  );

  if (loading) {
    return (
      <div className="mt-6 space-y-4 animate-fade-in">
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-32 rounded-xl" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
          <Skeleton className="h-96 rounded-xl lg:col-span-3" />
          <Skeleton className="h-96 rounded-xl lg:col-span-2" />
        </div>
        <Skeleton className="h-96 rounded-xl" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="mt-6 rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-destructive">
        {error}
      </div>
    );
  }

  const totalAmount = chartTotal;

  return (
    <div className="mt-6 space-y-4 animate-fade-in">
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <KpiCard
          title={t("expensesAnalytics.total")}
          amount={summary?.total.amount ?? 0}
          changePct={summary?.total.change_pct}
          compareLabel={compareLabel}
          icon={Briefcase}
          iconWrapClass="bg-violet-100 dark:bg-violet-950/40"
          iconClass="text-violet-600"
          tone="purple"
        />
        <KpiCard
          title={t("expensesAnalytics.logistics")}
          amount={summary?.logistics.amount ?? 0}
          changePct={summary?.logistics.change_pct}
          compareLabel={compareLabel}
          icon={Truck}
          iconWrapClass="bg-violet-100 dark:bg-violet-950/40"
          iconClass="text-violet-600"
          tone="purple"
        />
        <KpiCard
          title={t("expensesAnalytics.promotion")}
          amount={summary?.promotion.amount ?? 0}
          changePct={summary?.promotion.change_pct}
          compareLabel={compareLabel}
          icon={Flame}
          iconWrapClass="bg-orange-100 dark:bg-orange-950/40"
          iconClass="text-orange-600"
          tone="orange"
        />
        <KpiCard
          title={t("expensesAnalytics.storage")}
          amount={summary?.storage.amount ?? 0}
          changePct={summary?.storage.change_pct}
          compareLabel={compareLabel}
          icon={Package}
          iconWrapClass="bg-cyan-100 dark:bg-cyan-950/40"
          iconClass="text-cyan-600"
          tone="cyan"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <div className="bg-card rounded-xl border border-border shadow-sm p-5 lg:col-span-3 chart-container">
          <ChartTitle
            title={t("expensesAnalytics.byServices")}
            hint={t("expensesAnalytics.byServicesHint")}
          />
          {barData.length === 0 ? (
            <p className="text-sm text-muted-foreground py-16 text-center">{t("expensesAnalytics.empty")}</p>
          ) : (
            <div className="h-[340px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={barData}
                  layout="vertical"
                  margin={{ top: 4, right: 96, left: 8, bottom: 4 }}
                  barCategoryGap="18%"
                >
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="hsl(var(--border))" />
                  <XAxis
                    type="number"
                    domain={[0, Math.max(totalAmount, 1)]}
                    ticks={[0, 0.25, 0.5, 0.75, 1].map((p) => Math.max(totalAmount, 1) * p)}
                    tickFormatter={(v) => `${Math.round((Number(v) / Math.max(totalAmount, 1)) * 100)}%`}
                    tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={160}
                    tick={{ fill: "hsl(var(--foreground))", fontSize: 12 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    formatter={(value: number) => [formatMoneyNoDecimals(value, "сум"), t("expensesAnalytics.amount")]}
                    contentStyle={{
                      borderRadius: 8,
                      border: "1px solid hsl(var(--border))",
                      background: "hsl(var(--card))",
                    }}
                  />
                  <Bar dataKey="amount" radius={[0, 6, 6, 0]} maxBarSize={28}>
                    {barData.map((entry) => (
                      <Cell key={entry.name} fill={entry.fill} />
                    ))}
                    <LabelList
                      dataKey="amount"
                      position="right"
                      formatter={(v: number) => formatMoneyNoDecimals(v, "сум")}
                      style={{ fill: "hsl(var(--foreground))", fontSize: 12, fontWeight: 600 }}
                    />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        <div className="bg-card rounded-xl border border-border shadow-sm p-5 lg:col-span-2 chart-container">
          <ChartTitle
            title={t("expensesAnalytics.structure")}
            hint={t("expensesAnalytics.structureHint")}
          />
          {donutData.length === 0 ? (
            <p className="text-sm text-muted-foreground py-16 text-center">{t("expensesAnalytics.empty")}</p>
          ) : (
            <div className="flex flex-col h-[340px]">
              <div className="relative flex-1 min-h-0">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={donutData}
                      dataKey="value"
                      nameKey="name"
                      innerRadius="58%"
                      outerRadius="82%"
                      paddingAngle={2}
                      stroke="hsl(var(--card))"
                      strokeWidth={2}
                    >
                      {donutData.map((entry) => (
                        <Cell key={entry.name} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value: number, name: string) => [
                        formatMoneyNoDecimals(value, "сум"),
                        name,
                      ]}
                      contentStyle={{
                        borderRadius: 8,
                        border: "1px solid hsl(var(--border))",
                        background: "hsl(var(--card))",
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                  <div className="text-xl font-bold text-foreground">{formatMillions(totalAmount)}</div>
                  <div className="text-xs text-muted-foreground">{t("expensesAnalytics.totalShort")}</div>
                </div>
              </div>
              <div className="mt-2 space-y-1.5 max-h-36 overflow-y-auto pr-1">
                {donutData.map((item) => (
                  <div key={item.name} className="flex items-center justify-between gap-2 text-sm">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: item.fill }} />
                      <span className="truncate text-muted-foreground">{item.name}</span>
                    </div>
                    <span className="font-medium tabular-nums shrink-0">{item.share.toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="bg-card rounded-xl border border-border shadow-sm p-5 chart-container">
        <ChartTitle
          title={t("expensesAnalytics.weekly")}
          hint={t("expensesAnalytics.weeklyHint")}
        />
        {weeklyChartData.length === 0 || stackKeys.length === 0 ? (
          <p className="text-sm text-muted-foreground py-16 text-center">{t("expensesAnalytics.empty")}</p>
        ) : (
          <div className="h-[360px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={weeklyChartData} margin={{ top: 28, right: 12, left: 8, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
                <XAxis
                  dataKey="label"
                  tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tickFormatter={(v) => formatMillions(Number(v))}
                  tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                  axisLine={false}
                  tickLine={false}
                  width={56}
                />
                <Tooltip
                  formatter={(value: number, name: string) => [
                    formatMoneyNoDecimals(value, "сум"),
                    name,
                  ]}
                  labelFormatter={(label) => String(label)}
                  contentStyle={{
                    borderRadius: 8,
                    border: "1px solid hsl(var(--border))",
                    background: "hsl(var(--card))",
                  }}
                />
                <Legend
                  verticalAlign="bottom"
                  height={36}
                  iconType="circle"
                  wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
                />
                {stackKeys.map((key, idx) => (
                  <Bar
                    key={key}
                    dataKey={key}
                    stackId="expenses"
                    fill={colorByName[key] ?? FALLBACK_PALETTE[idx % FALLBACK_PALETTE.length]}
                    radius={idx === stackKeys.length - 1 ? [4, 4, 0, 0] : [0, 0, 0, 0]}
                    maxBarSize={72}
                  >
                    {idx === stackKeys.length - 1 && (
                      <LabelList
                        dataKey="total"
                        position="top"
                        formatter={(v: number) => formatMillions(v)}
                        style={{ fill: "hsl(var(--foreground))", fontSize: 12, fontWeight: 600 }}
                      />
                    )}
                  </Bar>
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}
