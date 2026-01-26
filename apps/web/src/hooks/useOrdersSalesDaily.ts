import { useQuery } from "@tanstack/react-query";
import { apiGet, buildQueryParams } from "@/lib/api";

interface OrdersSalesDailyPoint {
  date: string; // YYYY-MM-DD
  orders_qty: number;
  buyouts_qty: number;
  returns_qty: number;
  stock_qty: number;
  revenue_sum: number;
  profit_sum: number;
  avg_check: number;
}

interface OrdersSalesDailyResponse {
  points: OrdersSalesDailyPoint[];
  period: {
    code: string;
    date_from: string;
    date_to: string;
  };
  filters: {
    shop_id: string | null;
  };
}

interface UseOrdersSalesDailyParams {
  periodCode?: string;
  shopId?: string | null;
  groupBy?: "day" | "week" | "month";
}

export function useOrdersSalesDaily({ periodCode = "30d", shopId = null, groupBy = "day" }: UseOrdersSalesDailyParams) {
  return useQuery({
    queryKey: ['ordersSalesDaily', periodCode, shopId, groupBy],
    queryFn: async () => {
      const params = buildQueryParams({ period: periodCode, shopId, group_by: groupBy });
      return await apiGet<OrdersSalesDailyResponse>("/api/charts/orders-sales-daily", params);
    },
    retry: 1,
    refetchOnWindowFocus: false,
  });
}

export type { OrdersSalesDailyPoint, OrdersSalesDailyResponse };
