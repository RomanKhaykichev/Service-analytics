import { useQuery } from "@tanstack/react-query";
import { apiGet, buildQueryParams } from "@/lib/api";
import type { PeriodCode } from "@/lib/types";

interface StockDailyPoint {
  date: string;
  orders: number;
  stock: number;
}

interface StockDailyResponse {
  points: StockDailyPoint[];
  period: {
    code: string;
    date_from: string;
    date_to: string;
  };
  filters: {
    shop_id: string | null;
  };
}

interface UseStockDailyParams {
  periodCode: PeriodCode;
  shopId?: string | null;
}

export function useStockDaily({ periodCode, shopId }: UseStockDailyParams) {
  const { data, isLoading: loading, error } = useQuery({
    queryKey: ['stockDaily', periodCode, shopId],
    queryFn: async () => {
      const params = buildQueryParams({ period: periodCode, shopId });
      return await apiGet<StockDailyResponse>("/api/charts/stock-daily", params);
    },
  });

  return { 
    points: data?.points ?? [], 
    loading, 
    error: error ? (error instanceof Error ? error.message : "Failed to load stock daily") : null,
    period: data?.period ?? null,
    filters: data?.filters ?? null
  };
}
