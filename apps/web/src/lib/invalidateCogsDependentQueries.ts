import type { QueryClient } from "@tanstack/react-query";

/** Перезапрос метрик, зависящих от ручной себестоимости (как после перезагрузки страницы). */
export async function invalidateCogsDependentQueries(queryClient: QueryClient): Promise<void> {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ["kpiSummary"] }),
    queryClient.invalidateQueries({ queryKey: ["kpiMonthly"] }),
    queryClient.invalidateQueries({ queryKey: ["products-table"] }),
    queryClient.invalidateQueries({ queryKey: ["products-table-all"] }),
    queryClient.invalidateQueries({ queryKey: ["products-table-prev"] }),
    queryClient.invalidateQueries({ queryKey: ["revenueDaily"] }),
    queryClient.invalidateQueries({ queryKey: ["dailySummary"] }),
    queryClient.invalidateQueries({ queryKey: ["uzumServicesDaily"] }),
    queryClient.invalidateQueries({ queryKey: ["ordersSalesDaily"] }),
    queryClient.invalidateQueries({ queryKey: ["weeklyInsights"] }),
    queryClient.invalidateQueries({ queryKey: ["product-card-all-time-metrics"] }),
    queryClient.invalidateQueries({ queryKey: ["kpiSummary-product-extra"] }),
  ]);
}
