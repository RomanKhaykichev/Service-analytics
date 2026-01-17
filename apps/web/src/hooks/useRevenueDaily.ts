import { useState, useEffect } from "react";
import { apiGet, buildQueryParams } from "@/lib/api";
import type { PeriodCode } from "@/lib/types";

interface RevenuePoint {
  date: string;
  value: number;
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
  };
}

interface UseRevenueDailyParams {
  periodCode: PeriodCode;
  shopId?: string | null;
}

export function useRevenueDaily({ periodCode, shopId }: UseRevenueDailyParams) {
  const [points, setPoints] = useState<RevenuePoint[]>([]);
  const [period, setPeriod] = useState<{ code: string; date_from: string; date_to: string } | null>(null);
  const [filters, setFilters] = useState<{ shop_id: string | null } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadRevenue = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Map periodCode for revenue-daily API:
        // - "7d" -> "30d" (backend doesn't support 7d, use 30d)
        // - "all" -> "365d"
        // - otherwise use periodCode as-is
        const apiPeriod = 
          periodCode === "7d" ? "30d" :
          periodCode === "all" ? "365d" :
          periodCode;
        
        const params = buildQueryParams({ period: apiPeriod, shopId });
        const data = await apiGet<RevenueDailyResponse>("/api/charts/revenue-daily", params);
        setPoints(data.points);
        setPeriod(data.period);
        setFilters(data.filters);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load revenue");
      } finally {
        setLoading(false);
      }
    };

    loadRevenue();
  }, [periodCode, shopId]);

  return { points, loading, error, period, filters };
}
