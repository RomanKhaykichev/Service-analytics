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

interface UseDailySummaryParams {
  periodCode?: string;
  shopId?: string | null;
  shop?: string | null;
}

export function useDailySummary({
  periodCode = "30d",
  shopId = null,
  shop = null,
}: UseDailySummaryParams) {
  return useQuery({
    queryKey: ["dailySummary", periodCode, shop ?? "all", shopId ?? "all"],
    queryFn: async () => {
      const params = buildQueryParams({ period: periodCode, shopId, shop });
      return await apiGet<DailySummaryResponse>("/api/charts/daily-summary", params);
    },
    retry: 1,
    refetchOnWindowFocus: false,
  });
}
