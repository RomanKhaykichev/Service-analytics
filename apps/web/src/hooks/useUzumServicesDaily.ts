import { useQuery } from "@tanstack/react-query";
import { apiGet, buildQueryParams } from "@/lib/api";

interface UzumServicesPoint {
  date: string;
  storage: number;
  ads: number;
  fines: number;
  commission?: number;
  logistics?: number;
}

interface UzumServicesResponse {
  points: UzumServicesPoint[];
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

interface UseUzumServicesDailyParams {
  dateFrom: string;
  dateTo: string;
  shopId?: string | null;
  /** Shop name (string) from seller-storage for filtering by barcode */
  shop?: string | null;
}

export function useUzumServicesDaily({ dateFrom, dateTo, shopId, shop }: UseUzumServicesDailyParams) {
  const queryKey = ['uzumServicesDaily', dateFrom, dateTo, shop ?? 'all', shopId ?? 'all'];
  console.log("queryKey uzumServicesDaily", { date_from: dateFrom, date_to: dateTo, queryKey });
  const { data, isLoading: loading, error } = useQuery({
    queryKey,
    queryFn: async () => {
      const params = buildQueryParams({ date_from: dateFrom, date_to: dateTo, shopId, shop });
      const url = `/api/charts/uzum-services-daily?${new URLSearchParams(params as Record<string, string>).toString()}`;
      console.log("fetch useUzumServicesDaily", url);
      return await apiGet<UzumServicesResponse>("/api/charts/uzum-services-daily", params);
    },
    enabled: !!dateFrom && !!dateTo,
  });

  return { 
    points: data?.points ?? [], 
    loading, 
    error: error ? (error instanceof Error ? error.message : "Failed to load UZUM services daily") : null,
    period: data?.period ?? null,
    filters: data?.filters ?? null
  };
}
