import { useQuery } from "@tanstack/react-query";
import { apiGet, buildQueryParams } from "@/lib/api";
import type { PeriodCode } from "@/lib/types";

interface RevenuePoint {
  date: string;
  revenue: number;
  orders: number;
  averageCheck: number;
}

interface RevenueDailyResponse {
  points: RevenuePoint[];
  period: {
    code: string;
    date_from: string;
    date_to: string;
  };
  filters: {
    shop_id: string | null;
    shop: string | null;
  };
}

interface UseRevenueDailyParams {
  periodCode: PeriodCode;
  shopId?: string | null;
  /** Shop name (string) from seller-storage for filtering by barcode */
  shop?: string | null;
}

export function useRevenueDaily({ periodCode, shopId, shop }: UseRevenueDailyParams) {
  const { data, isLoading: loading, error } = useQuery({
    queryKey: ['revenueDaily', periodCode, shop ?? 'all', shopId ?? 'all'],
    queryFn: async () => {
      const params = buildQueryParams({ period: periodCode, shopId, shop });
      return await apiGet<RevenueDailyResponse>("/api/charts/revenue-daily", params);
    },
  });

  return { 
    points: data?.points ?? [], 
    loading, 
    error: error ? (error instanceof Error ? error.message : "Failed to load revenue") : null,
    period: data?.period ?? null,
    filters: data?.filters ?? null
  };
}
