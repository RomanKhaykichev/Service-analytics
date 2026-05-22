import { useState } from "react";
import { Warehouse, Wallet, ChevronDown, Sparkles, Upload, TrendingDown, BarChart3 } from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";
import { useSummaryWeeklyInsights, type WeeklyInsightProduct } from "@/hooks/useSummaryWeeklyInsights";
import { formatCurrency, formatPercent } from "@/lib/formatters";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface SummaryWeeklyInsightsProps {
  referenceDate: string | null | undefined;
  shop?: string | null;
  onOpenProduct?: (product: WeeklyInsightProduct) => void;
}

interface InsightRowProps {
  icon: React.ReactNode;
  children: React.ReactNode;
}

/** Иконка в том же виде, что в SummaryBlock, но с цветом блока. */
function InsightRow({ icon, children }: InsightRowProps) {
  return (
    <li className="flex items-start gap-2">
      <div className="flex-shrink-0 mt-0.5">{icon}</div>
      <span>{children}</span>
    </li>
  );
}

function WeeklyInsightsEmptyState() {
  const { t } = useLanguage();
  const bullets = [
    {
      text: t("summary.weeklyInsights.emptyBullet1"),
      icon: <Wallet className="w-4 h-4 text-success" />,
    },
    {
      text: t("summary.weeklyInsights.emptyBullet2"),
      icon: <Warehouse className="w-4 h-4 text-primary" />,
    },
    {
      text: t("summary.weeklyInsights.emptyBullet3"),
      icon: <TrendingDown className="w-4 h-4 text-destructive" />,
    },
    {
      text: t("summary.weeklyInsights.emptyBullet4"),
      icon: <BarChart3 className="w-4 h-4 text-warning" />,
    },
  ];

  return (
    <div className="mt-2 text-sm text-muted-foreground">
      <ul className="space-y-1.5 pl-1">
        {bullets.map((item) => (
          <li key={item.text} className="flex items-start gap-2">
            <span className="text-primary shrink-0">•</span>
            <div className="flex-shrink-0 mt-0.5">{item.icon}</div>
            <span>{item.text}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ProductNameLink({
  name,
  onClick,
}: {
  name: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="font-semibold text-foreground underline underline-offset-2 decoration-primary/50 hover:text-primary hover:decoration-primary transition-colors"
    >
      &quot;{name}&quot;
    </button>
  );
}

export function SummaryWeeklyInsights({
  referenceDate,
  shop,
  onOpenProduct,
}: SummaryWeeklyInsightsProps) {
  const { t } = useLanguage();
  const { data, loading, hasData } = useSummaryWeeklyInsights(referenceDate, shop);
  const [isExpanded, setIsExpanded] = useState(true);
  const showEmptyState = !loading && !hasData;

  const isEmptyTitle = showEmptyState;
  const blockTitle = isEmptyTitle
    ? t("summary.weeklyInsights.emptyIntro")
    : t("summary.weeklyInsights.title");
  const collapseLabel = isExpanded
    ? t("summary.weeklyInsights.collapse")
    : t("summary.weeklyInsights.expand");

  const header = (
    <button
      type="button"
      onClick={() => setIsExpanded((v) => !v)}
      className="w-full flex items-center justify-between gap-2 text-left rounded-md -mx-1 px-1 py-0.5 hover:bg-violet-100/60 dark:hover:bg-violet-900/30 transition-colors"
      aria-expanded={isExpanded}
      aria-label={collapseLabel}
    >
      <h3 className="font-semibold text-foreground flex items-center gap-1.5 min-w-0">
        {isEmptyTitle ? (
          <>
            <Upload className="w-4 h-4 shrink-0 text-primary" aria-hidden />
            <span className="text-left">{blockTitle}</span>
          </>
        ) : (
          <>
            {blockTitle}
            <Sparkles className="w-4 h-4 shrink-0 text-primary" aria-hidden />
          </>
        )}
      </h3>
      <ChevronDown
        className={cn(
          "w-4 h-4 shrink-0 text-muted-foreground transition-transform duration-200",
          isExpanded && "rotate-180"
        )}
      />
    </button>
  );

  if (loading) {
    return (
      <div className="mt-6 rounded-xl border border-violet-200/80 dark:border-violet-800/50 bg-violet-50/50 dark:bg-violet-950/20 p-4">
        {header}
        {isExpanded && (
          <div className="mt-2 space-y-1.5">
            <Skeleton className="h-5 w-full" />
            <Skeleton className="h-5 w-full" />
            <Skeleton className="h-5 w-full" />
          </div>
        )}
      </div>
    );
  }

  if (showEmptyState) {
    return (
      <div className="mt-6 rounded-xl border border-violet-200/80 dark:border-violet-800/50 bg-violet-50/50 dark:bg-violet-950/20 p-4 shadow-sm">
        {header}
        {isExpanded && <WeeklyInsightsEmptyState />}
      </div>
    );
  }

  if (!data) return null;

  const storageVerb = data.storageIncreased
    ? t("summary.weeklyInsights.storageIncreased")
    : t("summary.weeklyInsights.storageDecreased");
  const storagePct = formatPercent(Math.abs(data.storageChangePercent), 1);
  const storageDelta = data.storageWeekDelta;
  const storageDeltaFormatted =
    storageDelta > 0
      ? `+${formatCurrency(storageDelta)}`
      : storageDelta < 0
        ? `−${formatCurrency(Math.abs(storageDelta))}`
        : formatCurrency(0);
  const sumLabel = t("common.sum");

  const fill = (template: string, vars: Record<string, string>) =>
    Object.entries(vars).reduce(
      (s, [k, v]) => s.replaceAll(`{${k}}`, v),
      template
    );

  const storageChangeText = fill(t("summary.weeklyInsights.storageChange"), {
    verb: storageVerb,
    percent: storagePct,
  });
  const storageSuffix = fill(t("summary.weeklyInsights.storageSuffix"), {
    amount: storageDeltaFormatted,
  });
  const storageChangeColor = data.storageIncreased
    ? "text-destructive"
    : "text-success";

  const handleOpenProduct = (entry: WeeklyInsightProduct | null) => {
    if (entry && onOpenProduct) onOpenProduct(entry);
  };

  return (
    <div className="mt-6 rounded-xl border border-violet-200/80 dark:border-violet-800/50 bg-violet-50/50 dark:bg-violet-950/20 p-4 shadow-sm">
      {header}
      {isExpanded && (
        <ul className="mt-2 text-sm text-muted-foreground space-y-1.5">
          <InsightRow
            icon={
              <div className="text-primary">
                <Warehouse className="w-4 h-4" />
              </div>
            }
          >
            {t("summary.weeklyInsights.storagePrefix")}
            <span className={cn("font-semibold", storageChangeColor)}>
              {storageChangeText}
            </span>
            {storageSuffix}
          </InsightRow>

          {data.minProfitProduct && (
            <InsightRow
              icon={
                <div className="text-destructive">
                  <Wallet className="w-4 h-4" />
                </div>
              }
            >
              {t("summary.weeklyInsights.minProfitBeforeName")}
              <ProductNameLink
                name={data.minProfitProduct.name}
                onClick={() => handleOpenProduct(data.minProfitProduct)}
              />
              {t("summary.weeklyInsights.minProfitAfterName")}
              <span className="text-destructive font-semibold">
                {formatCurrency(data.minProfitProduct.profit)} {sumLabel}
              </span>
            </InsightRow>
          )}

          {data.maxProfitProduct && (
            <InsightRow
              icon={
                <div className="text-success">
                  <Wallet className="w-4 h-4" />
                </div>
              }
            >
              {t("summary.weeklyInsights.maxProfitBeforeName")}
              <ProductNameLink
                name={data.maxProfitProduct.name}
                onClick={() => handleOpenProduct(data.maxProfitProduct)}
              />
              {t("summary.weeklyInsights.maxProfitAfterName")}
              <span className="text-success font-semibold">
                {formatCurrency(data.maxProfitProduct.profit)} {sumLabel}
              </span>
            </InsightRow>
          )}
        </ul>
      )}
    </div>
  );
}
