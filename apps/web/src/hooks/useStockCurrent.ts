import { useState, useEffect } from "react";
import { apiGet, buildQueryParams } from "@/lib/api";

interface StockItem {
  barcode: string;
  sku: string;
  product_name: string | null;
  stock_qty: number | null;
  coverage_days: number | null;
  turnover_days: number | null;
  fee_total_30d: number | null;
  storage_type: string | null;
  size_group: string | null;
}

interface StockResponse {
  items: StockItem[];
  filters: {
    shop_id: string | null;
    q: string;
  };
}

interface UseStockCurrentParams {
  limit: number;
  shopId?: string | null;
}

export function useStockCurrent({ limit, shopId }: UseStockCurrentParams) {
  const [items, setItems] = useState<StockItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadStock = async () => {
      try {
        setLoading(true);
        setError(null);
        const params = buildQueryParams({ limit: String(limit), shopId });
        const data = await apiGet<StockResponse>("/api/charts/stock-current", params);
        setItems(data.items);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load stock");
      } finally {
        setLoading(false);
      }
    };

    loadStock();
  }, [limit, shopId]);

  return { items, loading, error };
}
