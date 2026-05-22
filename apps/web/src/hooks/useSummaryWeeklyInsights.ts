import { useMemo } from "react";
import { useQueries } from "@tanstack/react-query";
import { useAuth } from "./useAuth";
import { apiGet, buildQueryParams } from "@/lib/api";
import { getWeeklyInsightRanges } from "@/lib/weekRanges";
import type { ProductsTableItemType } from "@/components/dashboard/ProductsView";

interface KpiSummaryStorage {
  uzumStorage: number;
}

interface ProductsTableResponse {
  items: ProductsTableItemType[];
}

export interface WeeklyInsightProduct {
  name: string;
  profit: number;
  item: ProductsTableItemType;
}

export interface SummaryWeeklyInsightsData {
  storageChangePercent: number;
  /** Разница расходов на хранение: последние 7 дней − предыдущие 7 дней */
  storageWeekDelta: number;
  storageIncreased: boolean;
  minProfitProduct: WeeklyInsightProduct | null;
  maxProfitProduct: WeeklyInsightProduct | null;
}

function productGroupKey(item: ProductsTableItemType): string {
  return (item.product_id || item.product_name || item.barcode || "").trim();
}

function aggregateProfitByProduct(items: ProductsTableItemType[]): Map<string, WeeklyInsightProduct> {
  const map = new Map<string, WeeklyInsightProduct>();
  for (const item of items) {
    const key = productGroupKey(item);
    if (!key) continue;
    const name = (item.product_name ?? "").trim() || "—";
    const profit = item.profit ?? 0;
    const existing = map.get(key);
    if (!existing) {
      map.set(key, { name, profit, item });
    } else {
      map.set(key, { name: existing.name, profit: existing.profit + profit, item: existing.item });
    }
  }
  return map;
}

function findMinMaxProfit(
  map: Map<string, WeeklyInsightProduct>
): { min: WeeklyInsightProduct | null; max: WeeklyInsightProduct | null } {
  let min: WeeklyInsightProduct | null = null;
  let max: WeeklyInsightProduct | null = null;
  for (const entry of map.values()) {
    if (min == null || entry.profit < min.profit) min = entry;
    if (max == null || entry.profit > max.profit) max = entry;
  }
  return { min, max };
}

export function useSummaryWeeklyInsights(referenceDate: string | null | undefined, shop?: string | null) {
  const { user } = useAuth();
  const ranges = referenceDate ? getWeeklyInsightRanges(referenceDate) : null;

  const queries = useQueries({
    queries: ranges
      ? [
          {
            queryKey: ["weeklyInsights", "storage-prev", ranges.prevWeekFrom, ranges.prevWeekTo, shop ?? "all"],
            queryFn: () =>
              apiGet<KpiSummaryStorage>(
                "/api/kpi/summary",
                buildQueryParams({
                  date_from: ranges.prevWeekFrom,
                  date_to: ranges.prevWeekTo,
                  shop: shop ?? undefined,
                })
              ),
            enabled: !!user,
          },
          {
            queryKey: ["weeklyInsights", "storage-last", ranges.lastWeekFrom, ranges.lastWeekTo, shop ?? "all"],
            queryFn: () =>
              apiGet<KpiSummaryStorage>(
                "/api/kpi/summary",
                buildQueryParams({
                  date_from: ranges.lastWeekFrom,
                  date_to: ranges.lastWeekTo,
                  shop: shop ?? undefined,
                })
              ),
            enabled: !!user,
          },
          {
            queryKey: ["weeklyInsights", "products", ranges.lastWeekFrom, ranges.lastWeekTo, shop ?? "all"],
            queryFn: () =>
              apiGet<ProductsTableResponse>(
                "/api/charts/products-table",
                buildQueryParams({
                  date_from: ranges.lastWeekFrom,
                  date_to: ranges.lastWeekTo,
                  shop: shop ?? undefined,
                })
              ),
            enabled: !!user,
          },
        ]
      : [],
  });

  const loading = ranges ? queries.some((q) => q.isLoading) : false;
  const error = queries.find((q) => q.error)?.error;
  const productsItems = queries[2]?.data?.items ?? [];
  const hasData = productsItems.length > 0;

  const data = useMemo((): SummaryWeeklyInsightsData | null => {
    if (!ranges || queries.length < 3 || !hasData) return null;
    const prevStorage = queries[0].data?.uzumStorage ?? 0;
    const lastStorage = queries[1].data?.uzumStorage ?? 0;
    const items = productsItems;

    let storageChangePercent = 0;
    if (prevStorage > 0) {
      storageChangePercent = ((lastStorage - prevStorage) / prevStorage) * 100;
    } else if (lastStorage > 0) {
      storageChangePercent = 100;
    }

    const byProduct = aggregateProfitByProduct(items);
    const { min, max } = findMinMaxProfit(byProduct);

    return {
      storageChangePercent,
      storageWeekDelta: lastStorage - prevStorage,
      storageIncreased: lastStorage >= prevStorage,
      minProfitProduct: min,
      maxProfitProduct: max,
    };
  }, [ranges, queries, hasData, productsItems]);

  return { data, loading, error, hasData };
}
