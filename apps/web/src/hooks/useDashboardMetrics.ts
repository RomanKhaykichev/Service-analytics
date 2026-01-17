import { useState, useEffect, useMemo } from "react";
import { useAuth } from "./useAuth";
import { apiGet } from "@/lib/api";
import { startOfYear, subDays, format, startOfDay, endOfDay } from "date-fns";

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

interface DateRange {
  from: Date;
  to: Date;
}

function getDateRange(period: string): DateRange {
  const now = new Date();
  const to = endOfDay(now);
  let from: Date;

  switch (period) {
    case "7days":
      from = startOfDay(subDays(now, 7));
      break;
    case "14days":
      from = startOfDay(subDays(now, 14));
      break;
    case "30days":
      from = startOfDay(subDays(now, 30));
      break;
    case "90days":
      from = startOfDay(subDays(now, 90));
      break;
    default:
      from = startOfDay(subDays(now, 30));
  }

  return { from, to };
}

export function useDashboardMetrics(period: string = "30days", shopId?: string) {
  const { user } = useAuth();
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const dateRange = useMemo(() => getDateRange(period), [period]);

  useEffect(() => {
    if (!user) {
      setLoading(false);
      return;
    }

    const fetchMetrics = async () => {
      setLoading(true);
      setError(null);

      try {
        // TODO: Replace with actual API calls to backend
        // For now, return empty metrics to allow app to run
        console.warn("useDashboardMetrics: Using placeholder data. Backend API integration needed.");

        // Placeholder metrics (all zeros)
        const cumulativeRevenue = 0;
        const ordersCount = 0;
        const ordersValue = 0;
        const processingCount = 0;
        const processingValue = 0;
        const completedCount = 0;
        const completedValue = 0;
        const returnsCount = 0;
        const returnsValue = 0;
        const returnRate = 0;
        const averageCheck = 0;
        const revenue = 0;
        const totalExpenses = 0;
        const profit = 0;
        const salesProfitability = 0;
        const roi = 0;
        const revenueTrend = 0;
        const lostRevenue = 0;
        const uzumCommission = 0;
        const uzumLogistics = 0;
        const uzumAds = 0;
        const uzumFines = 0;
        const productCost = 0;
        const stockQuantity = 0;
        const stockCost = 0;
        const stockRetailPrice = 0;

        setMetrics({
          cumulativeRevenue,
          ordersCount,
          ordersValue,
          processingCount,
          processingValue,
          completedCount,
          completedValue,
          returnsCount,
          returnsValue,
          returnRate,
          averageCheck,
          revenue,
          totalExpenses,
          profit,
          salesProfitability,
          roi,
          revenueTrend,
          lostRevenue,
          uzumCommission,
          uzumLogistics,
          uzumAds,
          uzumFines,
          productCost,
          stockQuantity,
          stockCost,
          stockRetailPrice,
        });
      } catch (err) {
        console.error("Error fetching dashboard metrics:", err);
        setError(err instanceof Error ? err.message : "Ошибка загрузки данных");
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();
  }, [user, dateRange]);

  return { metrics, loading, error };
}
