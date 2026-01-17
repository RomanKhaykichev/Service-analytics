import { useState, useEffect } from "react";
import { useAuth } from "./useAuth";
import { apiGet, buildQueryParams } from "@/lib/api";
import type { PeriodCode } from "@/lib/types";

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
  uzumFines: number;
  productCost: number;

  // Склад
  stockQuantity: number;
  stockCost: number;
  stockRetailPrice: number;
}

export function useDashboardMetrics(periodCode: PeriodCode = "30d", shopId?: string) {
  const { user } = useAuth();
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) {
      setLoading(false);
      return;
    }

    const fetchMetrics = async () => {
      setLoading(true);
      setError(null);

      try {
        // Call KPI summary API with periodCode and shopId
        const params = buildQueryParams({ period: periodCode, shopId });
        const data = await apiGet<DashboardMetrics>("/api/kpi/summary", params);
        setMetrics(data);
      } catch (err) {
        console.error("Error fetching dashboard metrics:", err);
        setError(err instanceof Error ? err.message : "Ошибка загрузки данных");
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();
  }, [user, periodCode, shopId]);

  return { metrics, loading, error };
}
