import { useQuery } from "@tanstack/react-query";
import { useAuth } from "./useAuth";
import { apiGet } from "@/lib/api";

/**
 * Общая накопительная выручка пользователя за всё время.
 * Не зависит от фильтров магазина и периода — запрос без shop/period.
 * QueryKey фиксированный, рефетч при смене фильтров не выполняется.
 */
export function useCumulativeRevenueGlobal() {
  const { user } = useAuth();

  const { data, isLoading, error } = useQuery({
    queryKey: ["kpi", "cumulativeRevenue", "global"],
    queryFn: async () => {
      const res = await apiGet<{ cumulativeRevenue: number; cumulativeRevenueYear: number }>("/api/kpi/cumulative-revenue");
      return { cumulativeRevenue: res.cumulativeRevenue, cumulativeRevenueYear: res.cumulativeRevenueYear };
    },
    enabled: !!user,
  });

  return {
    cumulativeRevenue: data?.cumulativeRevenue ?? 0,
    cumulativeRevenueYear: data?.cumulativeRevenueYear ?? new Date().getFullYear(),
    loading: isLoading,
    error: error ? (error instanceof Error ? error.message : "Ошибка загрузки") : null,
  };
}
