import { useLanguage } from "@/contexts/LanguageContext";

interface RevenueProgressBarProps {
  current: number;
  target: number;
  /** Год последней даты в выгрузке — отображается под надписью «Накопительная выручка» */
  year?: number;
  compact?: boolean;
}

export function RevenueProgressBar({
  current,
  target,
  year,
  compact = false
}: RevenueProgressBarProps) {
  const { t } = useLanguage();
  const percentage = Math.min(current / target * 100, 100);
  const displayCurrent = Math.min(current, target);
  const isOverTarget = current > target;
  const exceededBy = Math.max(current - target, 0);
  const targetMillions = target / 1_000_000;
  const scaleStep = targetMillions / 5;
  const scaleValues = [0, scaleStep, scaleStep * 2, scaleStep * 3, scaleStep * 4, targetMillions];

  const formatBillions = (num: number) => {
    const billions = num / 1_000_000_000;
    const formatted =
      Math.abs(billions - Math.round(billions)) < 1e-9
        ? billions.toFixed(0)
        : billions.toFixed(1).replace(".", ",");
    return `${formatted} ${t("progress.billion")}`;
  };

  const formatNumber = (num: number) => {
    if (num >= 1_000_000_000) return formatBillions(num);
    if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(0)} ${t("progress.mln")}`;
    if (num >= 1_000) return `${(num / 1_000).toFixed(0)} ${t("progress.thousand")}`;
    return num.toString();
  };

  const formatScaleLabel = (value: number, index: number) => {
    if (value === 0) return "0";
    if (index === scaleValues.length - 1) return formatBillions(target);
    return `${Math.round(value)} ${t("progress.mln")}`;
  };

  if (compact) {
    return (
      <div className="h-10 gap-2 sm:gap-3 border border-purple-300/30 shadow rounded-lg w-full max-w-xl bg-gradient-to-r from-purple-50 to-violet-50 dark:from-purple-950/30 dark:to-violet-950/30 px-3 sm:px-4 flex items-center">
        <div className="flex items-baseline gap-1.5 flex-shrink-0 min-w-0">
          <span className="text-xs font-medium text-purple-700 dark:text-purple-300 whitespace-nowrap">
            {t("block.revenueProgress")}
          </span>
          {year != null && (
            <span className="text-[10px] text-purple-600/80 dark:text-purple-400/80">{year}</span>
          )}
        </div>
        <div className="relative flex-1 min-w-[80px]">
          <div className="relative h-2 bg-purple-100 dark:bg-purple-900/40 rounded-full overflow-hidden">
            <div
              className="absolute inset-y-0 left-0 bg-gradient-to-r from-purple-500 via-violet-500 to-fuchsia-500 rounded-full transition-all duration-500"
              style={{ width: `${percentage}%` }}
            />
          </div>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <span
            className={`text-xs font-semibold whitespace-nowrap ${isOverTarget ? "text-red-600 dark:text-red-400" : "text-purple-700 dark:text-purple-300"}`}
          >
            {formatNumber(displayCurrent)} / {formatNumber(target)}
          </span>
          {isOverTarget && (
            <span className="text-[10px] font-medium text-red-600/90 dark:text-red-400/90 whitespace-nowrap">
              +{formatNumber(exceededBy)}
            </span>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-purple-50 to-violet-50 dark:from-purple-950/30 dark:to-violet-950/30 p-4 border border-purple-200/50 dark:border-purple-700/30 shadow rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <div className="flex flex-col">
          <span className="text-base font-medium text-purple-700 dark:text-purple-300">
            {t('block.revenueProgress')}
          </span>
          {year != null && (
            <span className="text-sm text-purple-600/80 dark:text-purple-400/80">{year}</span>
          )}
        </div>
        <span className={`text-base font-semibold ${isOverTarget ? "text-red-600 dark:text-red-400" : "text-purple-600 dark:text-purple-400"}`}>
          {formatNumber(displayCurrent)} / {formatNumber(target)} {t('common.sum')}
        </span>
      </div>
      {isOverTarget && (
        <div className="mb-2 text-right">
          <span className="text-sm font-medium text-red-600/90 dark:text-red-400/90">
            +{formatNumber(exceededBy)}
          </span>
        </div>
      )}
      <div className="relative h-4 bg-purple-100 dark:bg-purple-900/40 rounded-full overflow-hidden">
        <div 
          className="absolute inset-y-0 left-0 bg-gradient-to-r from-purple-500 via-violet-500 to-fuchsia-500 rounded-full transition-all duration-500 shadow-lg shadow-purple-500/30" 
          style={{ width: `${percentage}%` }} 
        />
        <div className="absolute inset-0 flex justify-between items-center px-1">
          {scaleValues.map((_, index) => (
            <div 
              key={index} 
              className={`w-0.5 h-3 rounded-full ${index === 0 || index === 5 ? "bg-transparent" : "bg-purple-400/60 dark:bg-purple-300/60"}`} 
            />
          ))}
        </div>
      </div>
      <div className="flex justify-between mt-1.5">
        {scaleValues.map((value, index) => (
          <span key={index} className="text-xs text-purple-600/80 dark:text-purple-400/80">
            {formatScaleLabel(value, index)}
          </span>
        ))}
      </div>
    </div>
  );
}