import { useQuery } from "@tanstack/react-query";
import { useAuth } from "./useAuth";
import { apiGet } from "@/lib/api";

interface SalesDateRangeResponse {
  min_date: string | null;
  max_date: string | null;
  last_updated_at?: string | null;
}

/**
 * Fetches min/max date from fact_sales (sells-report "Дата создания") for the current user.
 * No shop filter — bounds are global for all sales.
 */
export function useSalesDateRange() {
  const { user } = useAuth();

  const { data, isLoading: loading, error } = useQuery({
    queryKey: ["salesDateRange"],
    queryFn: async () => apiGet<SalesDateRangeResponse>("/api/filters/date-bounds"),
    enabled: !!user,
  });

  return {
    minDate: data?.min_date ?? null,
    maxDate: data?.max_date ?? null,
    lastUpdatedAt: data?.last_updated_at ?? null,
    loading,
    error: error ? (error instanceof Error ? error.message : "Ошибка загрузки границ дат") : null,
  };
}
