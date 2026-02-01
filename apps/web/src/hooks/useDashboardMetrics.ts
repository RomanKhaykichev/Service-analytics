import { useQuery } from "@tanstack/react-query";
import { useAuth } from "./useAuth";
import { apiGet, buildQueryParams } from "@/lib/api";

interface DashboardMetrics {
  // Накопительная выручка (не фильтруется по периоду)
  cumulativeRevenue: number;

  // Продажи
  ordersCount: number;
  ordersValue: number;
  processingCount: number;
  processingValue: number;
  completedCount: number;
  completedValue: number;
  returnsCount: number;
  returnsValue: number;
  returnRate: number;
  averageCheck: number;

  // Финансы
  revenue: number;
  totalExpenses: number;
  profit: number;
  salesProfitability: number;
  roi: number;
  revenueTrend: number;
  lostRevenue: number;

  // Расходы
  uzumCommission: number;
  uzumLogistics: number;
  uzumAds: number;
  uzumStorage: number;
  uzumFines: number;
  taxes1pct: number;
  productCost: number;
  extraExpenses: number;

  // Склад
  stockQuantity: number;
  stockCost: number;
  stockRetailPrice: number;
  stockSkuTotal: number;
  stockSkuWithStock: number;
  stockSnapshotAt: string | null;
  stockHasData: boolean;
  stockIsZero: boolean;
  stockZeroReason: string | null;
  stockSource: 'leftout_old' | null;
}

export function useDashboardMetrics(dateFrom: string, dateTo: string, shopId?: string, shop?: string) {
  const { user } = useAuth();

  const { data: metrics, isLoading: loading, error } = useQuery({
    queryKey: ['kpiSummary', dateFrom, dateTo, shopId, shop],
    queryFn: async () => {
      const params = shop
        ? buildQueryParams({ date_from: dateFrom, date_to: dateTo, shop })
        : buildQueryParams({ date_from: dateFrom, date_to: dateTo, shopId });
      return await apiGet<DashboardMetrics>("/api/kpi/summary", params);
    },
    enabled: !!user && !!dateFrom && !!dateTo,
  });

  return { 
    metrics: metrics ?? null, 
    loading, 
    error: error ? (error instanceof Error ? error.message : "Ошибка загрузки данных") : null 
  };
}
