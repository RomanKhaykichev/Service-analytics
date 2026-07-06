import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/api";

export interface TrialShopOption {
  shop_id: string;
  shop_name: string;
}

export interface TrialShopSelectionStatus {
  is_trial: boolean;
  needs_selection: boolean;
  trial_display_shop: string | null;
  loaded_shops: TrialShopOption[];
}

export function useTrialShopSelection(enabled = true) {
  const queryClient = useQueryClient();

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["trialShopSelection"],
    queryFn: async () => {
      try {
        return await apiGet<TrialShopSelectionStatus>("/api/trial/shop-selection", undefined, {
          timeoutMs: 10_000,
        });
      } catch {
        return {
          is_trial: false,
          needs_selection: false,
          trial_display_shop: null,
          loaded_shops: [],
        } satisfies TrialShopSelectionStatus;
      }
    },
    enabled,
    staleTime: 15_000,
    retry: false,
    refetchOnWindowFocus: true,
  });

  const selectShop = async (shopName: string) => {
    await apiPost<{ trial_display_shop: string }>("/api/trial/shop-selection", {
      shop: shopName,
    });
    await queryClient.invalidateQueries({ queryKey: ["trialShopSelection"] });
    await queryClient.invalidateQueries({ queryKey: ["storageShops"] });
  };

  return {
    status: data,
    loading: isLoading,
    refetch,
    selectShop,
    needsSelection: Boolean(data?.needs_selection),
    trialDisplayShop: data?.trial_display_shop ?? null,
    isTrial: Boolean(data?.is_trial),
  };
}
