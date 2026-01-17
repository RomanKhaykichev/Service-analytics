import { useState, useEffect, useMemo } from "react";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "./useAuth";
import { startOfYear, subDays, format, startOfDay, endOfDay } from "date-fns";

interface DashboardMetrics {
  // Накопительная выручка (не фильтруется по периоду)
  cumulativeRevenue: number;

  // Продажи
  ordersCount: number;
  ordersValue: number;
  processingCount: number;
  processingValue: number;
  completedCount: number;
  completedValue: number;
  returnsCount: number;
  returnsValue: number;
  returnRate: number;
  averageCheck: number;

  // Финансы
  revenue: number;
  totalExpenses: number;
  profit: number;
  salesProfitability: number;
  roi: number;
  revenueTrend: number;
  lostRevenue: number;

  // Расходы
  uzumCommission: number;
  uzumLogistics: number;
  uzumAds: number;
  uzumFines: number;
  productCost: number;

  // Склад
  stockQuantity: number;
  stockCost: number;
  stockRetailPrice: number;
}

interface DateRange {
  from: Date;
  to: Date;
}

function getDateRange(period: string): DateRange {
  const now = new Date();
  const to = endOfDay(now);
  let from: Date;

  switch (period) {
    case "7days":
      from = startOfDay(subDays(now, 7));
      break;
    case "14days":
      from = startOfDay(subDays(now, 14));
      break;
    case "30days":
      from = startOfDay(subDays(now, 30));
      break;
    case "90days":
      from = startOfDay(subDays(now, 90));
      break;
    default:
      from = startOfDay(subDays(now, 30));
  }

  return { from, to };
}

export function useDashboardMetrics(period: string = "30days", shopId?: string) {
  const { user } = useAuth();
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const dateRange = useMemo(() => getDateRange(period), [period]);

  useEffect(() => {
    if (!user) {
      setLoading(false);
      return;
    }

    const fetchMetrics = async () => {
      setLoading(true);
      setError(null);

      try {
        const fromDate = format(dateRange.from, "yyyy-MM-dd");
        const toDate = format(dateRange.to, "yyyy-MM-dd");
        const yearStart = format(startOfYear(new Date()), "yyyy-MM-dd");

        // Calculate previous period for trend comparison
        const periodDays = Math.ceil((dateRange.to.getTime() - dateRange.from.getTime()) / (1000 * 60 * 60 * 24));
        const prevFrom = format(subDays(dateRange.from, periodDays), "yyyy-MM-dd");
        const prevTo = format(subDays(dateRange.to, periodDays), "yyyy-MM-dd");

        // Fetch all sales data for current period
        const { data: salesData, error: salesError } = await supabase
          .from("sales")
          .select("*")
          .gte("created_date", fromDate)
          .lte("created_date", toDate);

        if (salesError) throw salesError;

        // Fetch sales for previous period (for trend)
        const { data: prevSalesData, error: prevSalesError } = await supabase
          .from("sales")
          .select("revenue")
          .eq("status", "завершен")
          .gte("created_date", prevFrom)
          .lte("created_date", prevTo);

        if (prevSalesError) throw prevSalesError;

        // Fetch cumulative revenue from start of year (not filtered by period)
        const { data: yearSalesData, error: yearSalesError } = await supabase
          .from("sales")
          .select("revenue")
          .gte("created_date", yearStart);

        if (yearSalesError) throw yearSalesError;

        // Fetch expenses data
        const { data: expensesData, error: expensesError } = await supabase
          .from("expenses")
          .select("*")
          .gte("write_off_date", fromDate)
          .lte("write_off_date", toDate);

        if (expensesError) throw expensesError;

        // Fetch inventory snapshots (latest)
        const { data: inventoryData, error: inventoryError } = await supabase
          .from("inventory_snapshots")
          .select("*, product_variants(cost_price)")
          .order("snapshot_date", { ascending: false })
          .limit(1000);

        if (inventoryError) throw inventoryError;

        // Fetch storage costs for lost revenue calculation
        const { data: storageData, error: storageError } = await supabase
          .from("storage_costs")
          .select("avg_daily_sales_15d, fbo_stock_total, variant_id")
          .order("snapshot_date", { ascending: false });

        if (storageError) throw storageError;

        // Calculate metrics
        const sales = salesData || [];
        const expenses = expensesData || [];
        const inventory = inventoryData || [];
        const storage = storageData || [];
        const yearSales = yearSalesData || [];
        const prevSales = prevSalesData || [];

        // Накопительная выручка с начала года
        const cumulativeRevenue = yearSales.reduce((sum, s) => sum + (Number(s.revenue) || 0), 0);

        // Продажи - Заказы (все статусы)
        const ordersCount = sales.reduce((sum, s) => sum + (s.quantity || 0), 0);
        const ordersValue = sales.reduce((sum, s) => sum + ((s.quantity || 0) * (Number(s.price) || 0)), 0);

        // В обработке
        const processingSales = sales.filter(s => s.status === "в обработке");
        const processingCount = processingSales.reduce((sum, s) => sum + (s.quantity || 0), 0);
        const processingValue = processingSales.reduce((sum, s) => sum + (Number(s.revenue) || 0), 0);

        // Выкупы (завершен)
        const completedSales = sales.filter(s => s.status === "завершен");
        const completedCount = completedSales.reduce((sum, s) => sum + (s.quantity || 0), 0);
        const completedValue = completedSales.reduce((sum, s) => sum + (Number(s.revenue) || 0), 0);

        // Возвраты
        const cancelledSales = sales.filter(s => s.status === "отменен");
        const returnsCount = sales.reduce((sum, s) => sum + (s.returns || 0), 0);
        const returnsValue = cancelledSales.reduce((sum, s) => sum + ((s.returns || 0) * (Number(s.price) || 0)), 0);

        // Процент возврата
        const returnRate = ordersCount > 0 ? (returnsCount / ordersCount) * 100 : 0;

        // Средний чек
        const averageCheck = completedCount > 0 ? completedValue / completedCount : 0;

        // Финансы - Выручка (завершен)
        const revenue = completedValue;

        // Себестоимость (в обработке + завершен)
        const activeStatusSales = sales.filter(s => s.status === "в обработке" || s.status === "завершен");
        const productCost = activeStatusSales.reduce((sum, s) => sum + ((Number(s.cost_price) || 0) * (s.quantity || 0)), 0);

        // Расходы
        const uzumCommission = sales.reduce((sum, s) => sum + (Number(s.marketplace_commission) || 0), 0);
        const uzumLogistics = sales.reduce((sum, s) => sum + (Number(s.logistics_fee) || 0), 0);
        
        // Реклама UZUM (источник = маркетинг, тип операции = оплата)
        const adsExpenses = expenses.filter(e => 
          e.source?.toLowerCase().includes("маркетинг") && 
          e.operation_type?.toLowerCase().includes("оплата")
        );
        const uzumAds = adsExpenses.reduce((sum, e) => sum + (Number(e.total_amount) || 0), 0);

        // Штрафы UZUM (услуга содержит слово ШТРАФ)
        const fineExpenses = expenses.filter(e => 
          e.service_description?.toUpperCase().includes("ШТРАФ")
        );
        const uzumFines = fineExpenses.reduce((sum, e) => sum + (Number(e.total_amount) || 0), 0);

        // Общие расходы
        const totalExpenses = uzumCommission + uzumLogistics + uzumAds + uzumFines + productCost;

        // Прибыль
        const profit = revenue - totalExpenses;

        // Рентабельность продаж
        const completedCost = completedSales.reduce((sum, s) => sum + (Number(s.cost_price) || 0), 0);
        const salesProfitability = completedCost > 0 ? (completedValue / completedCost) : 0;

        // ROI = (Выручка - Себестоимость) / Себестоимость * 100%
        const roi = productCost > 0 ? ((revenue - productCost) / productCost) * 100 : 0;

        // Тренд выручки
        const prevRevenue = prevSales.reduce((sum, s) => sum + (Number(s.revenue) || 0), 0);
        const revenueTrend = prevRevenue > 0 ? ((revenue - prevRevenue) / prevRevenue) * 100 : 0;

        // Упущенная выручка
        // Условие: FBO stock = 0, расчет = avg_daily_sales_15d * price * 15
        let lostRevenue = 0;
        const outOfStockVariants = storage.filter(s => s.fbo_stock_total === 0);
        for (const storageItem of outOfStockVariants) {
          const avgDailySales = Number(storageItem.avg_daily_sales_15d) || 0;
          // Find average price for this variant from sales
          const variantSales = sales.filter(s => s.variant_id === storageItem.variant_id);
          const avgPrice = variantSales.length > 0 
            ? variantSales.reduce((sum, s) => sum + (Number(s.price) || 0), 0) / variantSales.length 
            : 0;
          lostRevenue += avgDailySales * avgPrice * 15;
        }

        // Склад
        // Группируем по variant_id и берем только последние записи
        const latestInventory = new Map<string, typeof inventory[0]>();
        for (const inv of inventory) {
          if (inv.variant_id && !latestInventory.has(inv.variant_id)) {
            latestInventory.set(inv.variant_id, inv);
          }
        }
        const uniqueInventory = Array.from(latestInventory.values());

        const stockQuantity = uniqueInventory.reduce((sum, inv) => sum + (inv.marketplace_total || 0), 0);
        
        // Себестоимость товара на складе
        const stockCost = uniqueInventory.reduce((sum, inv) => {
          const costPrice = inv.product_variants?.cost_price || 0;
          return sum + ((inv.marketplace_total || 0) * Number(costPrice));
        }, 0);

        // Розничная цена товаров
        const stockRetailPrice = uniqueInventory.reduce((sum, inv) => sum + (Number(inv.potential_revenue_total) || 0), 0);

        setMetrics({
          cumulativeRevenue,
          ordersCount,
          ordersValue,
          processingCount,
          processingValue,
          completedCount,
          completedValue,
          returnsCount,
          returnsValue,
          returnRate,
          averageCheck,
          revenue,
          totalExpenses,
          profit,
          salesProfitability,
          roi,
          revenueTrend,
          lostRevenue,
          uzumCommission,
          uzumLogistics,
          uzumAds,
          uzumFines,
          productCost,
          stockQuantity,
          stockCost,
          stockRetailPrice,
        });
      } catch (err) {
        console.error("Error fetching dashboard metrics:", err);
        setError(err instanceof Error ? err.message : "Ошибка загрузки данных");
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();
  }, [user, dateRange]);

  return { metrics, loading, error };
}
