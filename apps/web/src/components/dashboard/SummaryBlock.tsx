import { ReactNode, useState, useEffect } from "react";
import { ChevronDown, ChevronUp, HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { RevenueTrendIcon } from "@/components/dashboard/RevenueTrendIcon";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface MetricItem {
  icon: ReactNode;
  label: string | ReactNode;
  value: string;
  subValue?: string;
  trend?: "up" | "down" | "neutral";
  trendValue?: string;
  tooltip?: string;
  /** Дополнительный контрол рядом с подписью (например, ссылка-редактирование). */
  action?: ReactNode;
}

interface SummaryBlockProps {
  title: string;
  titleColor: string;
  metrics: MetricItem[];
  defaultExpanded?: boolean;
  showToggleButton?: boolean;
  onToggle?: () => void;
  // Опциональная вторая группа метрик с заголовком и tooltip
  secondaryMetrics?: MetricItem[];
  secondaryGroupTitle?: string;
  secondaryGroupTooltip?: string;
  // Кастомные стили
  customBorderClass?: string;
  customMinHeight?: string;
  customPadding?: string;
  customSpacing?: string;
  customBackgroundClass?: string;
  customHeightClass?: string;
  customOverflowClass?: string;
  // Empty state (показывается вместо метрик)
  emptyState?: ReactNode;
}

export function SummaryBlock({
  title,
  titleColor,
  metrics,
  defaultExpanded = true,
  showToggleButton = false,
  onToggle,
  secondaryMetrics,
  secondaryGroupTitle,
  secondaryGroupTooltip,
  customBorderClass,
  customMinHeight,
  customPadding,
  customSpacing,
  customBackgroundClass,
  customHeightClass,
  customOverflowClass,
  emptyState,
}: SummaryBlockProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  // Синхронизируем локальное состояние с пропсом defaultExpanded
  useEffect(() => {
    setIsExpanded(defaultExpanded);
  }, [defaultExpanded]);

  const borderClass = customBorderClass || "border-border";
  const minHeightClass = customMinHeight || "";
  const backgroundClass = customBackgroundClass || "bg-card";
  const heightClass = customHeightClass || "h-full";
  const overflowClass = customOverflowClass || "overflow-hidden";

  return (
    <div className={cn(
      "rounded-xl border shadow-sm transition-all duration-200 flex flex-col",
      backgroundClass,
      borderClass,
      minHeightClass,
      heightClass,
      overflowClass
    )}>
      <div className="w-full flex items-center justify-between p-4">
        <h3 className={cn("text-sm font-bold uppercase tracking-wide", titleColor)}>
          {title}
        </h3>
        {showToggleButton && onToggle && (
          <button
            onClick={onToggle}
            className="flex items-center gap-2 px-2 py-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            {isExpanded ? (
              <>
                <ChevronUp className="w-4 h-4" />
                Свернуть блоки
              </>
            ) : (
              <>
                <ChevronDown className="w-4 h-4" />
                Развернуть блоки
              </>
            )}
          </button>
        )}
      </div>

      {isExpanded && (
        <div className={cn(
          "animate-fade-in flex flex-col",
          customPadding || "px-4 pb-4",
          customSpacing || "space-y-2",
          emptyState && "justify-center flex-1",
          !emptyState && "flex-auto"
        )}>
          {emptyState ? (
            emptyState
          ) : (
            <>
              {metrics.map((metric, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between py-2 border-b border-border/50 last:border-0"
                >
              <div className="flex items-center gap-2">
                <div className="text-muted-foreground">{metric.icon}</div>
                <span className="text-sm text-muted-foreground">{metric.label}</span>
                {metric.tooltip && (
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger>
                        <HelpCircle className="w-3 h-3 text-muted-foreground/50" />
                      </TooltipTrigger>
                      <TooltipContent>
                        <p className="text-xs max-w-48">{metric.tooltip}</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                )}
                {metric.action}
              </div>
              <div className="flex items-center gap-2">
                {(metric.trend === "up" || metric.trend === "down") && (
                  <RevenueTrendIcon trend={metric.trend} />
                )}
                <span className="text-sm font-semibold text-foreground whitespace-nowrap">
                  {metric.value}
                </span>
                {metric.subValue && (
                  <span className="text-xs text-muted-foreground">
                    / {metric.subValue}
                  </span>
                )}
                {metric.trendValue && (
                  <span
                    className={cn(
                      "text-xs font-medium px-1.5 py-0.5 rounded",
                      metric.trend === "up" && "text-success bg-success/10",
                      metric.trend === "down" && "text-destructive bg-destructive/10",
                      metric.trend === "neutral" && "text-muted-foreground bg-muted"
                    )}
                  >
                    {metric.trendValue}
                  </span>
                )}
                </div>
              </div>
              ))}
              
              {/* Вторая группа метрик с заголовком и tooltip */}
              {secondaryMetrics && secondaryMetrics.length > 0 && (
                <>
                  <div className="mt-3 pt-3 border-t border-border/50">
                    <div className="flex items-center justify-center gap-2 mb-2 px-1">
                      <span className={cn("text-xs font-semibold", titleColor, "opacity-75")}>
                        {secondaryGroupTitle || "Дополнительные метрики"}
                      </span>
                      {secondaryGroupTooltip && (
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger>
                              <HelpCircle className="w-3 h-3 text-muted-foreground/50" />
                            </TooltipTrigger>
                            <TooltipContent>
                              <p className="text-xs max-w-64">{secondaryGroupTooltip}</p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      )}
                    </div>
                    {secondaryMetrics.map((metric, index) => (
                      <div
                        key={`secondary-${index}`}
                        className="flex items-center justify-between py-2 border-b border-border/50 last:border-0"
                      >
                        <div className="flex items-center gap-2">
                          <div className="text-muted-foreground">{metric.icon}</div>
                          <span className="text-sm text-muted-foreground">{metric.label}</span>
                          {metric.tooltip && (
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger>
                                  <HelpCircle className="w-3 h-3 text-muted-foreground/50" />
                                </TooltipTrigger>
                                <TooltipContent>
                                  <p className="text-xs max-w-48">{metric.tooltip}</p>
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          )}
                          {metric.action}
                        </div>
                        <div className="flex items-center gap-2">
                          {(metric.trend === "up" || metric.trend === "down") && (
                            <RevenueTrendIcon trend={metric.trend} />
                          )}
                          <span className="text-sm font-semibold text-foreground whitespace-nowrap">
                            {metric.value}
                          </span>
                          {metric.subValue && (
                            <span className="text-xs text-muted-foreground">
                              / {metric.subValue}
                            </span>
                          )}
                          {metric.trendValue && (
                            <span
                              className={cn(
                                "text-xs font-medium px-1.5 py-0.5 rounded",
                                metric.trend === "up" && "text-success bg-success/10",
                                metric.trend === "down" && "text-destructive bg-destructive/10",
                                metric.trend === "neutral" && "text-muted-foreground bg-muted"
                              )}
                            >
                              {metric.trendValue}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
