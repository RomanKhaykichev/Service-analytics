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
  const isOverBillion = current > 1_000_000_000;
  const exceededBy = Math.max(current - target, 0);
  const formatNumber = (num: number) => {
    if (num >= 1000000000) return `${(num / 1000000000).toFixed(0)} ${t('progress.billion')}`;
    if (num >= 1000000) return `${(num / 1000000).toFixed(0)} ${t('progress.mln')}`;
    if (num >= 1000) return `${(num / 1000).toFixed(0)} ${t('progress.thousand')}`;
    return num.toString();
  };

  const scaleValues = [0, 200, 400, 600, 800, 1000]; // in millions

  if (compact) {
    return (
      <div className="gap-3 sm:gap-4 py-3 border border-purple-300/30 shadow rounded-lg w-full bg-gradient-to-r from-purple-50 to-violet-50 dark:from-purple-950/30 dark:to-violet-950/30 px-3 sm:px-[30px] flex flex-col sm:flex-row sm:items-center sm:justify-center">
        <div className="flex flex-col flex-shrink-0">
          <span className="text-sm sm:text-base font-medium text-purple-700 dark:text-purple-300">
            {t('block.revenueProgress')}
          </span>
          {year != null && (
            <span className="text-xs sm:text-sm text-purple-600/80 dark:text-purple-400/80">{year}</span>
          )}
        </div>
        <div className="relative flex-1 min-w-0 mt-1 sm:mt-0">
          <div className="relative h-4 bg-purple-100 dark:bg-purple-900/40 rounded-full overflow-hidden">
            <div 
              className="absolute inset-y-0 left-0 bg-gradient-to-r from-purple-500 via-violet-500 to-fuchsia-500 rounded-full transition-all duration-500 shadow-lg shadow-purple-500/30" 
              style={{ width: `${percentage}%` }} 
            />
            <div className="absolute inset-0 flex justify-between items-center px-0.5">
              {scaleValues.map((_, index) => (
                <div 
                  key={index} 
                  className={`w-0.5 h-3 rounded-full ${index === 0 || index === 5 ? "bg-transparent" : "bg-purple-400/60 dark:bg-purple-300/60"}`} 
                />
              ))}
            </div>
          </div>
          {/* Scale labels below the bar */}
          <div className="flex justify-between mt-1">
            {scaleValues.map((value, index) => (
              <span key={index} className="text-[9px] sm:text-[10px] text-purple-600/70 dark:text-purple-400/70">
                {value === 0 ? '0' : value === 1000 ? `1 ${t('progress.billion')}` : `${value} ${t('progress.mln')}`}
              </span>
            ))}
          </div>
        </div>
        <div className="flex flex-col items-end flex-shrink-0 mt-1 sm:mt-0">
          <span className={`text-sm sm:text-base font-semibold ${isOverBillion ? "text-red-600 dark:text-red-400" : "text-purple-700 dark:text-purple-300"}`}>
            {formatNumber(displayCurrent)} / {formatNumber(target)}
          </span>
          {isOverBillion && (
            <span className="text-xs sm:text-sm font-medium text-red-600/90 dark:text-red-400/90">
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
        <span className={`text-base font-semibold ${isOverBillion ? "text-red-600 dark:text-red-400" : "text-purple-600 dark:text-purple-400"}`}>
          {formatNumber(displayCurrent)} / {formatNumber(target)} {t('common.sum')}
        </span>
      </div>
      {isOverBillion && (
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
            {value === 0 ? '0' : value === 1000 ? `1 ${t('progress.billion')}` : `${value} ${t('progress.mln')}`}
          </span>
        ))}
      </div>
    </div>
  );
}