import { Calendar, Store, BarChart3 } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface SummaryFiltersProps {
  period: string;
  store: string;
  onPeriodChange: (period: string) => void;
  onStoreChange: (store: string) => void;
  viewMode?: string;
  onViewModeChange?: (mode: string) => void;
  showViewMode?: boolean;
}

export function SummaryFilters({
  period,
  store,
  onPeriodChange,
  onStoreChange,
  viewMode = "day",
  onViewModeChange,
  showViewMode = false,
}: SummaryFiltersProps) {
  return (
    <div className="flex items-center gap-3">
      <Select value={store} onValueChange={onStoreChange}>
        <SelectTrigger className="w-[180px] bg-accent text-accent-foreground border-0 hover:bg-accent/90">
          <Store className="w-4 h-4 mr-2" />
          <SelectValue placeholder="Все продажи" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">Все продажи</SelectItem>
          <SelectItem value="store1">Магазин 1</SelectItem>
          <SelectItem value="store2">Магазин 2</SelectItem>
          <SelectItem value="store3">Магазин 3</SelectItem>
        </SelectContent>
      </Select>

      <Select value={period} onValueChange={onPeriodChange}>
        <SelectTrigger className="w-[180px] bg-accent text-accent-foreground border-0 hover:bg-accent/90">
          <Calendar className="w-4 h-4 mr-2" />
          <SelectValue placeholder="Последние 30 дней" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="week">Неделя</SelectItem>
          <SelectItem value="30days">Последние 30 дней</SelectItem>
          <SelectItem value="60days">60 дней</SelectItem>
          <SelectItem value="90days">90 дней</SelectItem>
          <SelectItem value="custom">Произвольный период</SelectItem>
        </SelectContent>
      </Select>

      {showViewMode && onViewModeChange && (
        <Select value={viewMode} onValueChange={onViewModeChange}>
          <SelectTrigger className="w-[140px] bg-accent text-accent-foreground border-0 hover:bg-accent/90">
            <BarChart3 className="w-4 h-4 mr-2" />
            <SelectValue placeholder="По дням" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="day">По дням</SelectItem>
            <SelectItem value="week">По неделям</SelectItem>
            <SelectItem value="month">По месяцам</SelectItem>
          </SelectContent>
        </Select>
      )}
    </div>
  );
}
