import {
  createContext,
  useContext,
  useMemo,
  useEffect,
  useCallback,
  useState,
  useRef,
  ReactNode,
} from "react";
import { useSearchParams } from "react-router-dom";
import { useSalesDateRange } from "@/hooks/useSalesDateRange";
import {
  getDefaultDateRange,
  getDefaultDateRangeInBounds,
  isValidRange,
  clampRange,
} from "@/lib/dateRange";

export interface DateRangeValue {
  dateFrom: string;
  dateTo: string;
}

interface DateRangeContextType {
  dateFrom: string;
  dateTo: string;
  setDateRange: (range: DateRangeValue) => void;
  minDate: string | null;
  maxDate: string | null;
  boundsLoading: boolean;
  hasBounds: boolean;
  defaultDateFrom: string | null;
  defaultDateTo: string | null;
}

const DateRangeContext = createContext<DateRangeContextType | null>(null);

export function DateRangeProvider({ children }: { children: ReactNode }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const { minDate, maxDate, loading: boundsLoading } = useSalesDateRange();
  const hasBounds = !!minDate && !!maxDate;

  const defaultRangeInBounds = useMemo(
    () => (hasBounds ? getDefaultDateRangeInBounds(minDate!, maxDate!) : null),
    [hasBounds, minDate, maxDate]
  );

  // Локальный state — источник истины для выбранного диапазона, чтобы при setDateRange сразу обновлялся контекст и шёл refetch
  const [rangeState, setRangeState] = useState<DateRangeValue | null>(null);
  // Не сбрасывать rangeState в эффекте синхронизации URL→state, если URL только что обновили мы (setDateRange).
  // Иначе после setSearchParams searchParams ещё старые → эффект сбрасывает rangeState → даты откатываются, refetch не идёт.
  const skipSyncFromSetDateRangeRef = useRef(false);

  const derivedFromUrl = useMemo(() => {
    const from = searchParams.get("date_from");
    const to = searchParams.get("date_to");
    if (hasBounds) {
      if (from && to && isValidRange(from, to) && from >= minDate! && to <= maxDate!)
        return { dateFrom: from, dateTo: to };
      return defaultRangeInBounds ?? { dateFrom: minDate!, dateTo: maxDate! };
    }
    if (from && to && isValidRange(from, to)) return { dateFrom: from, dateTo: to };
    return getDefaultDateRange();
  }, [searchParams, hasBounds, minDate, maxDate, defaultRangeInBounds]);

  const dateFrom = rangeState?.dateFrom ?? derivedFromUrl.dateFrom;
  const dateTo = rangeState?.dateTo ?? derivedFromUrl.dateTo;

  useEffect(() => {
    if (!hasBounds) return;
    const from = searchParams.get("date_from");
    const to = searchParams.get("date_to");
    const valid =
      from && to && isValidRange(from, to) && from >= minDate! && to <= maxDate!;
    if (!valid && defaultRangeInBounds) {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set("date_from", defaultRangeInBounds.dateFrom);
        next.set("date_to", defaultRangeInBounds.dateTo);
        return next;
      });
      setRangeState(null);
    }
  }, [hasBounds, minDate, maxDate, defaultRangeInBounds]);

  // При навигации (back/forward): если в URL другие даты, чем в state — сбрасываем state, чтобы показывать даты из URL.
  // Не сбрасываем, если URL только что обновили мы (setDateRange), т.к. searchParams могут ещё не обновиться.
  useEffect(() => {
    if (skipSyncFromSetDateRangeRef.current) {
      skipSyncFromSetDateRangeRef.current = false;
      return;
    }
    const from = searchParams.get("date_from");
    const to = searchParams.get("date_to");
    if (from && to && isValidRange(from, to)) {
      setRangeState((prev) => {
        if (prev && prev.dateFrom === from && prev.dateTo === to) return prev;
        return null;
      });
    }
  }, [searchParams.get("date_from"), searchParams.get("date_to")]);

  const setDateRange = useCallback(
    (range: DateRangeValue) => {
      const clamped = hasBounds
        ? clampRange(range.dateFrom, range.dateTo, minDate!, maxDate!)
        : range;
      if (!isValidRange(clamped.dateFrom, clamped.dateTo)) return;
      skipSyncFromSetDateRangeRef.current = true;
      setRangeState({ dateFrom: clamped.dateFrom, dateTo: clamped.dateTo });
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set("date_from", clamped.dateFrom);
        next.set("date_to", clamped.dateTo);
        return next;
      });
      console.log("[DateRange] setDateRange applied:", clamped.dateFrom, clamped.dateTo);
    },
    [hasBounds, minDate, maxDate, setSearchParams]
  );

  const value: DateRangeContextType = useMemo(
    () => ({
      dateFrom,
      dateTo,
      setDateRange,
      minDate: minDate ?? null,
      maxDate: maxDate ?? null,
      boundsLoading,
      hasBounds,
      defaultDateFrom: defaultRangeInBounds?.dateFrom ?? null,
      defaultDateTo: defaultRangeInBounds?.dateTo ?? null,
    }),
    [
      dateFrom,
      dateTo,
      setDateRange,
      minDate,
      maxDate,
      boundsLoading,
      hasBounds,
      defaultRangeInBounds,
    ]
  );

  return (
    <DateRangeContext.Provider value={value}>
      {children}
    </DateRangeContext.Provider>
  );
}

export function useDateRange(): DateRangeContextType {
  const ctx = useContext(DateRangeContext);
  if (!ctx) {
    throw new Error("useDateRange must be used within DateRangeProvider");
  }
  return ctx;
}
