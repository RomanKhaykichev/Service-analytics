import { useQuery } from "@tanstack/react-query";
import { apiGet, buildQueryParams } from "@/lib/api";

export interface DailySummaryPoint {
  date: string; // YYYY-MM-DD
  orders: number;
  buys: number;
  returns: number;
  revenue: number;
  commission: number;
  logistics: number;
  storage: number;
  ads: number;
  penalties: number;
  cogs: number;
  taxes: number;
  profit: number;
}

export interface DailySummaryResponse {
  points: DailySummaryPoint[];
  period: { code: string; date_from: string; date_to: string };
  filters: { shop_id: string | null; shop: string | null };
}

export type DailySummaryGranularity = "day" | "week" | "month";

interface UseDailySummaryParams {
  dateFrom: string;
  dateTo: string;
  shopId?: string | null;
  shop?: string | null;
  /** Chart aggregation: day | week | month. Omit or "day" for table (daily). */
  granularity?: DailySummaryGranularity;
}

export function useDailySummary({
  dateFrom,
  dateTo,
  shopId = null,
  shop = null,
  granularity = "day",
}: UseDailySummaryParams) {
  const queryKey = ["dailySummary", dateFrom, dateTo, shop ?? "all", shopId ?? "all", granularity];
  console.log("queryKey dailySummary", { date_from: dateFrom, date_to: dateTo, queryKey });
  return useQuery({
    queryKey,
    queryFn: async () => {
      const params = buildQueryParams({ date_from: dateFrom, date_to: dateTo, shopId, shop, granularity });
      const url = `/api/charts/daily-summary?${new URLSearchParams(params as Record<string, string>).toString()}`;
      console.log("fetch useDailySummary", url);
      return await apiGet<DailySummaryResponse>("/api/charts/daily-summary", params);
    },
    enabled: !!dateFrom && !!dateTo,
    retry: 1,
    refetchOnWindowFocus: false,
  });
}
