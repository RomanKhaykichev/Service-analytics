import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";

interface Shop {
  shop_id: string;
  shop_name?: string;
  locked?: boolean;
  is_trial_display?: boolean;
}

interface ShopsResponse {
  shops: Shop[];
}

/**
 * Hook to fetch shops from seller-storage file ONLY.
 * Returns DISTINCT shop names from stg_storage.shop_raw column (column "Магазин" from Excel).
 * Does NOT use dim_shop, sales, or any other sources - only seller-storage data.
 */
export function useStorageShops() {
  const { data, isLoading: loading, error } = useQuery({
    queryKey: ["storageShops"],
    queryFn: async () => {
      try {
        return await apiGet<ShopsResponse>("/api/storage/shops", undefined, { timeoutMs: 15_000 });
      } catch (err) {
        // Если endpoint ещё не готов - возвращаем пустой список (не падаем)
        console.warn("Failed to load storage shops, endpoint may not be ready:", err);
        return { shops: [] } as ShopsResponse;
      }
    },
    staleTime: 15_000,
    refetchOnWindowFocus: true,
  });

  return {
    shops: data?.shops ?? [],
    loading,
    error: error ? (error instanceof Error ? error.message : "Failed to load storage shops") : null,
  };
}
