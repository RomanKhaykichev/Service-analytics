import { useQuery } from "@tanstack/react-query";
import { apiGet, buildQueryParams } from "@/lib/api";

export interface RevenuePoint {
  date: string;
  revenue: number;
  orders: number;
  averageCheck: number;
  /** По карточке товара: возвраты по дням (формула из блока Продажи) */
  returns?: number;
  /** По карточке товара: прибыль по дням (формула из блока Финансы) */
  profit?: number;
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
  dateFrom: string;
  dateTo: string;
  shopId?: string | null;
  /** Shop name (string) from seller-storage for filtering by barcode */
  shop?: string | null;
  /** ID карточки товара — данные только по этому товару */
  productId?: string | null;
}

export function useRevenueDaily({ dateFrom, dateTo, shopId, shop, productId }: UseRevenueDailyParams) {
  const queryKey = ['revenueDaily', dateFrom, dateTo, shop ?? 'all', shopId ?? 'all', productId ?? 'all'];
  const { data, isLoading: loading, error } = useQuery({
    queryKey,
    queryFn: async () => {
      const params = buildQueryParams({ date_from: dateFrom, date_to: dateTo, shopId, shop, product_id: productId ?? undefined });
      const url = `/api/charts/revenue-daily?${new URLSearchParams(params as Record<string, string>).toString()}`;
      console.log("fetch useRevenueDaily", url);
      return await apiGet<RevenueDailyResponse>("/api/charts/revenue-daily", params);
    },
    enabled: !!dateFrom && !!dateTo,
  });

  return { 
    points: data?.points ?? [], 
    loading, 
    error: error ? (error instanceof Error ? error.message : "Failed to load revenue") : null,
    period: data?.period ?? null,
    filters: data?.filters ?? null
  };
}
