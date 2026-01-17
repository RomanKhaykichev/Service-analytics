import { useState, useEffect } from "react";
import { apiGet } from "@/lib/api";

interface Shop {
  shop_id: string;
  shop_name?: string;
}

interface ShopsResponse {
  shops: Shop[];
}

export function useShops() {
  const [shops, setShops] = useState<Shop[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadShops = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await apiGet<ShopsResponse>("/api/shops");
        setShops(data.shops);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load shops");
      } finally {
        setLoading(false);
      }
    };

    loadShops();
  }, []);

  return { shops, loading, error };
}
