import { Calendar, Store, BarChart3 } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { PeriodCode } from "@/lib/types";

interface Shop {
  shop_id: string;
  shop_name?: string | null;
}

const PERIOD_OPTIONS = [
  { value: "7d", label: "Неделя" },
  { value: "30d", label: "30 дней" },
  { value: "90d", label: "90 дней" },
  { value: "all", label: "Все данные" },
] as const;

interface SummaryFiltersProps {
  period: PeriodCode;
  store: string;
  onPeriodChange: (period: PeriodCode) => void;
  onStoreChange: (store: string) => void;
  viewMode?: string;
  onViewModeChange?: (mode: string) => void;
  showViewMode?: boolean;
  shops?: Shop[];
}

export function SummaryFilters({
  period,
  store,
  onPeriodChange,
  onStoreChange,
  viewMode = "day",
  onViewModeChange,
  showViewMode = false,
  shops = [],
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
          {shops.map((shop) => (
            <SelectItem key={shop.shop_id} value={shop.shop_id}>
              {shop.shop_name ?? shop.shop_id}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select value={period} onValueChange={onPeriodChange}>
        <SelectTrigger className="w-[180px] bg-accent text-accent-foreground border-0 hover:bg-accent/90">
          <Calendar className="w-4 h-4 mr-2" />
          <SelectValue placeholder="30 дней" />
        </SelectTrigger>
        <SelectContent>
          {PERIOD_OPTIONS.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
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
