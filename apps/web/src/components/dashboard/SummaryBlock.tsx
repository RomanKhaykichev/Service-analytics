import { ReactNode, useState, useEffect } from "react";
import { ChevronDown, ChevronUp, HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface MetricItem {
  icon: ReactNode;
  label: string;
  value: string;
  subValue?: string;
  trend?: "up" | "down" | "neutral";
  trendValue?: string;
  tooltip?: string;
}

interface SummaryBlockProps {
  title: string;
  titleColor: string;
  metrics: MetricItem[];
  defaultExpanded?: boolean;
  showToggleButton?: boolean;
  onToggle?: () => void;
}

export function SummaryBlock({
  title,
  titleColor,
  metrics,
  defaultExpanded = true,
  showToggleButton = false,
  onToggle,
}: SummaryBlockProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  // Синхронизируем локальное состояние с пропсом defaultExpanded
  useEffect(() => {
    setIsExpanded(defaultExpanded);
  }, [defaultExpanded]);

  return (
    <div className="bg-card rounded-xl border border-border shadow-sm overflow-hidden transition-all duration-200">
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
        <div className="px-4 pb-4 space-y-2 animate-fade-in">
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
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-foreground">
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
      )}
    </div>
  );
}
