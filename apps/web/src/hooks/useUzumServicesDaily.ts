import { useQuery } from "@tanstack/react-query";
import { apiGet, buildQueryParams } from "@/lib/api";
import type { PeriodCode } from "@/lib/types";

interface UzumServicesPoint {
  date: string;
  storage: number;
  ads: number;
  fines: number;
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
  };
}

interface UseUzumServicesDailyParams {
  periodCode: PeriodCode;
  shopId?: string | null; // Игнорируется на бэкенде, но передаётся для консистентности API
}

export function useUzumServicesDaily({ periodCode, shopId }: UseUzumServicesDailyParams) {
  const { data, isLoading: loading, error } = useQuery({
    queryKey: ['uzumServicesDaily', periodCode], // shopId не включаем, т.к. игнорируется
    queryFn: async () => {
      const params = buildQueryParams({ period: periodCode }); // shopId не передаём
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
