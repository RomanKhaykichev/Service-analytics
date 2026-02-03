import { useQuery } from "@tanstack/react-query";
import { useAuth } from "./useAuth";
import { apiGet, buildQueryParams } from "@/lib/api";

/** Один месяц — те же метрики, что в KPI summary (формулы как на Сводке). */
export interface MonthlyKpiItem {
  ordersCount: number;
  revenue: number;
  productCost: number;
  uzumCommission: number;
  uzumLogistics: number;
  uzumStorage: number;
  uzumAds: number;
  uzumFines: number;
  taxes1pct: number;
  extraExpenses: number;
  profit: number;
}

interface KpiSummaryResponse {
  ordersCount: number;
  revenue: number;
  productCost: number;
  uzumCommission: number;
  uzumLogistics: number;
  uzumStorage: number;
  uzumAds: number;
  uzumFines: number;
  taxes1pct: number;
  extraExpenses: number;
  profit: number;
}

function lastDayOfMonth(year: number, month: number): string {
  const d = new Date(year, month, 0);
  const day = String(d.getDate()).padStart(2, "0");
  const m = String(month).padStart(2, "0");
  return `${year}-${m}-${day}`;
}

/**
 * KPI по месяцам за год — те же формулы, что на вкладке Сводка (date_from/date_to по каждому месяцу).
 * Используется для таблицы «Финансовые показатели по месяцам».
 */
export function useMonthlyKpi(year: number, shop?: string) {
  const { user } = useAuth();
  const queryKey = ["kpiMonthly", year, shop ?? "all"];

  const { data: monthly, isLoading, error } = useQuery({
    queryKey,
    queryFn: async (): Promise<MonthlyKpiItem[]> => {
      const result: MonthlyKpiItem[] = [];
      for (let m = 1; m <= 12; m++) {
        const dateFrom = `${year}-${String(m).padStart(2, "0")}-01`;
        const dateTo = lastDayOfMonth(year, m);
        const params = shop
          ? buildQueryParams({ date_from: dateFrom, date_to: dateTo, shop })
          : buildQueryParams({ date_from: dateFrom, date_to: dateTo });
        const row = await apiGet<KpiSummaryResponse>("/api/kpi/summary", params);
        result.push({
          ordersCount: row.ordersCount ?? 0,
          revenue: row.revenue ?? 0,
          productCost: row.productCost ?? 0,
          uzumCommission: row.uzumCommission ?? 0,
          uzumLogistics: row.uzumLogistics ?? 0,
          uzumStorage: row.uzumStorage ?? 0,
          uzumAds: row.uzumAds ?? 0,
          uzumFines: row.uzumFines ?? 0,
          taxes1pct: row.taxes1pct ?? 0,
          extraExpenses: row.extraExpenses ?? 0,
          profit: row.profit ?? 0,
        });
      }
      return result;
    },
    enabled: !!user && !!year,
  });

  return {
    monthly: monthly ?? null,
    loading: isLoading,
    error: error ? (error instanceof Error ? error.message : "Ошибка загрузки данных") : null,
  };
}
