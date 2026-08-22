import { useQuery } from "@tanstack/react-query";
import { apiGet, buildQueryParams } from "@/lib/api";

export interface ExpensesKpiMetric {
  amount: number;
  change_pct: number | null;
}

export interface ExpensesSummary {
  total: ExpensesKpiMetric;
  logistics: ExpensesKpiMetric;
  promotion: ExpensesKpiMetric;
  storage: ExpensesKpiMetric;
  revenue: number;
  promotion_revenue_share_pct: number | null;
  compare_period_from: string | null;
  compare_period_to: string | null;
}

export interface ExpensesServiceItem {
  name: string;
  amount: number;
  share_pct: number;
  category: string;
}

export interface ExpensesWeekPart {
  name: string;
  amount: number;
}

export interface ExpensesWeekPoint {
  week_start: string;
  week_end: string;
  label: string;
  total: number;
  parts: ExpensesWeekPart[];
}

export interface ExpensesBreakdownResponse {
  summary: ExpensesSummary;
  services: ExpensesServiceItem[];
  weekly: ExpensesWeekPoint[];
  period: { code: string; date_from: string; date_to: string };
  filters: { shop_id: string | null; shop: string | null };
}

interface UseExpensesBreakdownParams {
  dateFrom: string;
  dateTo: string;
  shopId?: string | null;
  shop?: string | null;
  enabled?: boolean;
}

export function useExpensesBreakdown({
  dateFrom,
  dateTo,
  shopId,
  shop,
  enabled = true,
}: UseExpensesBreakdownParams) {
  const { data, isLoading: loading, error } = useQuery({
    queryKey: ["expensesBreakdown", dateFrom, dateTo, shop ?? "all", shopId ?? "all"],
    queryFn: async () => {
      const params = buildQueryParams({ date_from: dateFrom, date_to: dateTo, shopId, shop });
      return await apiGet<ExpensesBreakdownResponse>("/api/charts/expenses-breakdown", params);
    },
    enabled: enabled && !!dateFrom && !!dateTo,
  });

  return {
    summary: data?.summary ?? null,
    services: data?.services ?? [],
    weekly: data?.weekly ?? [],
    loading,
    error: error ? (error instanceof Error ? error.message : "Failed to load expenses breakdown") : null,
    period: data?.period ?? null,
  };
}
