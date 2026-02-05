import { useQuery } from "@tanstack/react-query";
import { apiGet, buildQueryParams } from "@/lib/api";

export interface ShipmentRecommendationItem {
  product_name: string | null;
  sku: string | null;
  barcode: string | null;
  stock: string | null;
  sales_per_day: string | null;
  recommended_qty: string;
  to_ship: string | null;
  /** Оборачиваемость (дней) из left-out-report_old для расчёта recommended_qty */
  turnover?: number | null;
}

interface ShipmentRecommendationsResponse {
  items: ShipmentRecommendationItem[];
}

/** shop — значение фильтра магазина (seller-storage, нормализованное имя); при "all" не передавать */
export function useShipmentRecommendations(shop?: string | null) {
  return useQuery({
    queryKey: ["shipment-recommendations", shop ?? "all"],
    queryFn: async () => {
      const params = shop ? buildQueryParams({ shop }) : undefined;
      return await apiGet<ShipmentRecommendationsResponse>("/api/charts/shipment-recommendations", params);
    },
  });
}
