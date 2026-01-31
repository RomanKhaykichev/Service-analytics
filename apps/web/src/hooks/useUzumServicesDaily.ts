import { useQuery } from "@tanstack/react-query";
import { apiGet, buildQueryParams } from "@/lib/api";
import type { PeriodCode } from "@/lib/types";

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
  periodCode: PeriodCode;
  shopId?: string | null;
  /** Shop name (string) from seller-storage for filtering by barcode */
  shop?: string | null;
}

export function useUzumServicesDaily({ periodCode, shopId, shop }: UseUzumServicesDailyParams) {
  const { data, isLoading: loading, error } = useQuery({
    queryKey: ['uzumServicesDaily', periodCode, shop ?? 'all', shopId ?? 'all'],
    queryFn: async () => {
      const params = buildQueryParams({ period: periodCode, shopId, shop });
      return await apiGet<UzumServicesResponse>("/api/charts/uzum-services-daily", params);
    },
  });

  return { 
    points: data?.points ?? [], 
    loading, 
    error: error ? (error instanceof Error ? error.message : "Failed to load UZUM services daily") : null,
    period: data?.period ?? null,
    filters: data?.filters ?? null
  };
}
