import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";

export interface ShipmentRecommendationItem {
  product_name: string | null;
  sku: string | null;
  barcode: string | null;
  stock: string | null;
  sales_per_day: string | null;
  recommended_qty: string;
  to_ship: string | null;
}

interface ShipmentRecommendationsResponse {
  items: ShipmentRecommendationItem[];
}

export function useShipmentRecommendations() {
  return useQuery({
    queryKey: ["shipment-recommendations"],
    queryFn: async () => {
      return await apiGet<ShipmentRecommendationsResponse>("/api/charts/shipment-recommendations");
    },
  });
}
