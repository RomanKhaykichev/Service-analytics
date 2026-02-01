import { useState } from "react";
import { Calendar, Store, BarChart3 } from "lucide-react";
import { format } from "date-fns";
import { ru } from "date-fns/locale";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { isValidRange } from "@/lib/dateRange";
import { Skeleton } from "@/components/ui/skeleton";

interface Shop {
  shop_id: string;
  shop_name?: string | null;
}

export interface DateRangeValue {
  dateFrom: string;
  dateTo: string;
}

interface SummaryFiltersProps {
  dateFrom: string;
  dateTo: string;
  onDateRangeChange: (range: DateRangeValue) => void;
  store: string;
  onStoreChange: (store: string) => void;
  viewMode?: string;
  onViewModeChange?: (mode: string) => void;
  showViewMode?: boolean;
  shops?: Shop[];
  /** Границы дат из fact_sales (sells-report). Если нет — пикер отключён. */
  minDate?: string;
  maxDate?: string;
  boundsLoading?: boolean;
  /** Дефолтный диапазон в границах (для кнопки «Сбросить»). */
  defaultDateFrom?: string;
  defaultDateTo?: string;
}

export function SummaryFilters({
  dateFrom,
  dateTo,
  onDateRangeChange,
  store,
  onStoreChange,
  viewMode = "day",
  onViewModeChange,
  showViewMode = false,
  shops = [],
  minDate,
  maxDate,
  boundsLoading = false,
  defaultDateFrom,
  defaultDateTo,
}: SummaryFiltersProps) {
  const [open, setOpen] = useState(false);
  const [draftFrom, setDraftFrom] = useState(dateFrom);
  const [draftTo, setDraftTo] = useState(dateTo);

  const hasBounds = !!minDate && !!maxDate;
  const periodDisabled = boundsLoading || !hasBounds;
  const canApply =
    hasBounds &&
    isValidRange(draftFrom, draftTo) &&
    draftFrom >= minDate &&
    draftTo <= maxDate;
  const displayLabel =
    dateFrom && dateTo
      ? `${format(new Date(dateFrom), "dd.MM.yyyy", { locale: ru })} – ${format(new Date(dateTo), "dd.MM.yyyy", { locale: ru })}`
      : "Период";

  const handleOpen = (isOpen: boolean) => {
    if (isOpen) {
      setDraftFrom(dateFrom);
      setDraftTo(dateTo);
    }
    setOpen(isOpen);
  };

  const handleApply = () => {
    if (!canApply) return;
    onDateRangeChange({ dateFrom: draftFrom, dateTo: draftTo });
    setOpen(false);
  };

  const handleReset = () => {
    const defFrom = defaultDateFrom ?? minDate ?? dateFrom;
    const defTo = defaultDateTo ?? maxDate ?? dateTo;
    setDraftFrom(defFrom);
    setDraftTo(defTo);
    onDateRangeChange({ dateFrom: defFrom, dateTo: defTo });
    setOpen(false);
  };

  const periodButton = (
    <Button
      variant="outline"
      className="w-[240px] justify-start text-left font-normal bg-accent text-accent-foreground border-0 hover:bg-accent/90"
      disabled={periodDisabled}
    >
      <Calendar className="w-4 h-4 mr-2 shrink-0" />
      <span className="truncate">{displayLabel}</span>
    </Button>
  );

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

      {boundsLoading ? (
        <Skeleton className="h-9 w-[240px]" />
      ) : !hasBounds ? (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="inline-block">{periodButton}</span>
            </TooltipTrigger>
            <TooltipContent>
              <p>Нет данных sells-report</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      ) : null}

      {hasBounds && (
        <Popover open={open} onOpenChange={handleOpen}>
          <PopoverTrigger asChild>{periodButton}</PopoverTrigger>
          <PopoverContent className="w-auto p-4" align="start">
            <div className="space-y-3">
              <div className="space-y-2">
                <Label htmlFor="period-from">От</Label>
                <Input
                  id="period-from"
                  type="date"
                  min={minDate}
                  max={draftTo || maxDate}
                  value={draftFrom}
                  onChange={(e) => setDraftFrom(e.target.value)}
                  className="w-full"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="period-to">До</Label>
                <Input
                  id="period-to"
                  type="date"
                  min={draftFrom || minDate}
                  max={maxDate}
                  value={draftTo}
                  onChange={(e) => setDraftTo(e.target.value)}
                  className="w-full"
                />
              </div>
              {!canApply && draftFrom && draftTo && (
                <p className="text-xs text-destructive">
                  {draftFrom > draftTo
                    ? "Дата «От» не может быть позже «До»"
                    : "Выберите даты в диапазоне данных"}
                </p>
              )}
              <div className="flex items-center gap-2 pt-2">
                <Button size="sm" onClick={handleApply} disabled={!canApply}>
                  Применить
                </Button>
                <Button size="sm" variant="outline" onClick={handleReset}>
                  Сбросить
                </Button>
              </div>
            </div>
          </PopoverContent>
        </Popover>
      )}

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
