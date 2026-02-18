import { useState } from "react";
import { Calendar, Store, BarChart3 } from "lucide-react";
import { format, parseISO, startOfYear, startOfMonth, subDays } from "date-fns";
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
import { cn } from "@/lib/utils";

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
  /** Показывать селект магазина (на вкладке "По дням" скрыт) */
  showStoreFilter?: boolean;
  /** Показывать выбор периода (на вкладке "Отгрузка" скрыт) */
  showPeriodFilter?: boolean;
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
  showStoreFilter = true,
  showPeriodFilter = true,
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
    console.log("[SummaryFilters] date range applied:", draftFrom, draftTo);
    onDateRangeChange({ dateFrom: draftFrom, dateTo: draftTo });
    setOpen(false);
  };

  const applyQuickRange = (kind: "7" | "30" | "Y") => {
    if (!hasBounds || !minDate || !maxDate) return;

    const end = parseISO(maxDate);
    let start: Date;
    if (kind === "7") start = subDays(end, 6);
    else if (kind === "30") start = subDays(end, 29);
    else start = startOfYear(end);

    // date-fns format avoids timezone shifting issues with toISOString().
    const startIso = format(start, "yyyy-MM-dd");
    const clampedFrom = startIso < minDate ? minDate : startIso;
    const clampedTo = maxDate;

    setDraftFrom(clampedFrom);
    setDraftTo(clampedTo);
    onDateRangeChange({ dateFrom: clampedFrom, dateTo: clampedTo });
    setOpen(false);
  };

  const handleReset = () => {
    if (!hasBounds || !maxDate) {
      const defFrom = defaultDateFrom ?? minDate ?? dateFrom;
      const defTo = defaultDateTo ?? maxDate ?? dateTo;
      setDraftFrom(defFrom);
      setDraftTo(defTo);
      onDateRangeChange({ dateFrom: defFrom, dateTo: defTo });
      setOpen(false);
      return;
    }
    
    // С начала месяца до максимальной даты
    const maxDateObj = parseISO(maxDate);
    const monthStart = startOfMonth(maxDateObj);
    const monthStartIso = format(monthStart, "yyyy-MM-dd");
    const clampedFrom = monthStartIso < (minDate ?? monthStartIso) ? (minDate ?? monthStartIso) : monthStartIso;
    const clampedTo = maxDate;
    
    setDraftFrom(clampedFrom);
    setDraftTo(clampedTo);
    onDateRangeChange({ dateFrom: clampedFrom, dateTo: clampedTo });
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
      {showStoreFilter && (
        <Select value={store} onValueChange={onStoreChange}>
          <SelectTrigger className="w-[180px] bg-accent text-accent-foreground border-0 hover:bg-accent/90">
            <Store className="w-4 h-4 mr-2" />
            <SelectValue placeholder="Все магазины" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Все магазины</SelectItem>
            {shops.map((shop) => (
              <SelectItem key={shop.shop_id} value={shop.shop_id}>
                {shop.shop_name ?? shop.shop_id}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}

      {showPeriodFilter && (boundsLoading ? (
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
      ) : null)}

      {showPeriodFilter && hasBounds && (
        <Popover open={open} onOpenChange={handleOpen}>
          <PopoverTrigger asChild>{periodButton}</PopoverTrigger>
          <PopoverContent className="w-auto p-4" align="start">
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-xs text-muted-foreground">Быстрый период</div>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    type="button"
                    variant="outline"
                    onClick={() => applyQuickRange("7")}
                  >
                    7
                  </Button>
                  <Button
                    size="sm"
                    type="button"
                    variant="outline"
                    onClick={() => applyQuickRange("30")}
                  >
                    30
                  </Button>
                  <Button
                    size="sm"
                    type="button"
                    variant="outline"
                    onClick={() => applyQuickRange("Y")}
                  >
                    Y
                  </Button>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Label htmlFor="period-from" className="text-xs w-8 shrink-0">От</Label>
                <Input
                  id="period-from"
                  type="date"
                  min={minDate}
                  max={draftTo || maxDate}
                  value={draftFrom}
                  onChange={(e) => setDraftFrom(e.target.value)}
                  className="h-8 text-sm"
                />
              </div>
              <div className="flex items-center gap-2">
                <Label htmlFor="period-to" className="text-xs w-8 shrink-0">До</Label>
                <Input
                  id="period-to"
                  type="date"
                  min={draftFrom || minDate}
                  max={maxDate}
                  value={draftTo}
                  onChange={(e) => setDraftTo(e.target.value)}
                  className="h-8 text-sm"
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
          <SelectTrigger
            className={cn(
              "w-[160px] min-w-[160px] h-10 shrink-0 font-normal",
              "bg-accent text-accent-foreground hover:bg-accent/90",
              "border border-transparent focus:border-border focus:ring-0 focus:ring-offset-0",
              "px-3 py-2 [&>span]:min-w-0 [&>span]:truncate"
            )}
          >
            <BarChart3 className="w-4 h-4 mr-2 shrink-0" />
            <SelectValue placeholder="По дням" />
          </SelectTrigger>
          <SelectContent className="min-w-[160px]">
            <SelectItem value="day" className="font-normal">
              По дням
            </SelectItem>
            <SelectItem value="week" className="font-normal">
              По неделям
            </SelectItem>
            <SelectItem value="month" className="font-normal">
              По месяцам
            </SelectItem>
          </SelectContent>
        </Select>
      )}
    </div>
  );
}
