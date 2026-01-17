import { LucideIcon, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

interface KPICardProps {
  title: string;
  value: string;
  change?: number;
  changeLabel?: string;
  icon: LucideIcon;
  iconColor?: string;
  trend?: "up" | "down" | "neutral";
  sparkline?: number[];
}

export function KPICard({
  title,
  value,
  change,
  changeLabel,
  icon: Icon,
  iconColor = "text-primary",
  trend = "neutral",
  sparkline,
}: KPICardProps) {
  const TrendIcon = trend === "up" ? TrendingUp : trend === "down" ? TrendingDown : Minus;

  return (
    <div className="kpi-card group animate-fade-in">
      <div className="flex items-start justify-between mb-3">
        <div
          className={cn(
            "w-10 h-10 rounded-lg flex items-center justify-center transition-transform group-hover:scale-110",
            iconColor === "text-primary" && "bg-primary-light",
            iconColor === "text-accent" && "bg-accent-light",
            iconColor === "text-success" && "bg-success/10",
            iconColor === "text-warning" && "bg-warning/10"
          )}
        >
          <Icon className={cn("w-5 h-5", iconColor)} />
        </div>
        
        {change !== undefined && (
          <div
            className={cn(
              "flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium",
              trend === "up" && "bg-success/10 text-success",
              trend === "down" && "bg-destructive/10 text-destructive",
              trend === "neutral" && "bg-muted text-muted-foreground"
            )}
          >
            <TrendIcon className="w-3 h-3" />
            <span>{change > 0 ? "+" : ""}{change}%</span>
          </div>
        )}
      </div>

      <div className="space-y-1">
        <p className="text-sm text-muted-foreground">{title}</p>
        <p className="text-2xl font-bold text-foreground">{value}</p>
        {changeLabel && (
          <p className="text-xs text-muted-foreground">{changeLabel}</p>
        )}
      </div>

      {/* Mini sparkline */}
      {sparkline && sparkline.length > 0 && (
        <div className="mt-3 flex items-end gap-0.5 h-8">
          {sparkline.map((val, i) => (
            <div
              key={i}
              className={cn(
                "flex-1 rounded-sm transition-all",
                trend === "up" ? "bg-success/60" : trend === "down" ? "bg-destructive/60" : "bg-primary/40"
              )}
              style={{ height: `${(val / Math.max(...sparkline)) * 100}%` }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
