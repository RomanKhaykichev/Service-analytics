import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Package, Warehouse, Download } from "lucide-react";
import * as XLSX from "xlsx";
import { toast } from "sonner";
import { useShipmentRecommendations } from "@/hooks/useShipmentRecommendations";
import type { ShipmentRecommendationItem } from "@/hooks/useShipmentRecommendations";
import { apiGet } from "@/lib/api";
import { useLanguage } from "@/contexts/LanguageContext";

/** Ключ строки для хранения рассчитанного значения (штрихкод или артикул) */
function rowKey(row: { barcode?: string | null; sku?: string | null }): string {
  return (row.barcode ?? row.sku ?? "").trim();
}

interface ShipmentViewProps {
  /** Фильтр по магазину (seller-storage); фильтрует таблицу через fact_storage_snapshot по баркодам */
  shop?: string | null;
  daysUntilShipment: number;
  setDaysUntilShipment: (v: number) => void;
  considerStock: string;
  setConsiderStock: (v: string) => void;
  /** Рассчитанные значения по ключу товара (barcode/sku); общие для всей таблицы до следующего пересчёта */
  calculatedRecommendedByKey: Record<string, number>;
  setCalculatedRecommended: (map: Record<string, number>) => void;
}

interface ShipmentRecommendationsResponse {
  items: ShipmentRecommendationItem[];
}

/** Парсим число из строки (дробные с запятой/точкой); NaN при пустом или нечисле */
function parseNum(s: string | null | undefined): number {
  if (s == null || s === "") return NaN;
  const n = Number(String(s).replace(",", ".").trim());
  return Number.isFinite(n) ? n : NaN;
}

export function ShipmentView({
  shop,
  daysUntilShipment,
  setDaysUntilShipment,
  considerStock,
  setConsiderStock,
  calculatedRecommendedByKey,
  setCalculatedRecommended,
}: ShipmentViewProps) {
  const { t } = useLanguage();
  const { data, isLoading, error } = useShipmentRecommendations(shop);
  const items = data?.items ?? [];
  const [calculateLoading, setCalculateLoading] = useState(false);

  const handleCalculate = async () => {
    setCalculateLoading(true);
    try {
      const res = await apiGet<ShipmentRecommendationsResponse>("/api/charts/shipment-recommendations");
      const allItems = res?.items ?? [];
      if (allItems.length === 0) return;
      const days = Math.max(0, Number(daysUntilShipment) || 0);
      const map: Record<string, number> = {};
      for (const row of allItems) {
        const key = rowKey(row);
        if (!key) continue;
        const salesPerDay = parseNum(row.sales_per_day);
        const turnover = row.turnover != null ? Number(row.turnover) : NaN;
        if (!Number.isFinite(salesPerDay) || salesPerDay < 0) {
          map[key] = 0;
          continue;
        }
        if (considerStock === "yes") {
          const t = Number.isFinite(turnover) ? turnover : 0;
          const factor = Math.max(0, 60 - t + days);
          map[key] = Math.ceil(factor * salesPerDay);
        } else {
          map[key] = Math.ceil(salesPerDay * 60);
        }
      }
      setCalculatedRecommended(map);
    } finally {
      setCalculateLoading(false);
    }
  };

  const handleExportXLSX = () => {
    const rows = items.map((row) => {
      const key = rowKey(row);
      const recommendedDisplay =
        key && calculatedRecommendedByKey[key] !== undefined
          ? String(calculatedRecommendedByKey[key])
          : row.recommended_qty;
      return {
        [t('shipment.product')]: row.product_name ?? "",
        [t('shipment.article')]: row.sku ?? "",
        [t('product.barcode')]: row.barcode ?? "",
        [t('shipment.inStock')]: row.stock ?? "",
        [t('shipment.salesPerDay')]: row.sales_per_day ?? "",
        [t('shipment.recommendedQty')]: recommendedDisplay,
        [t('shipment.plannedToShip')]: row.to_ship ?? "",
      };
    });
    const worksheet = XLSX.utils.json_to_sheet(rows);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, t('shipment.recommendations'));
    XLSX.writeFile(workbook, `отгрузка_${new Date().toISOString().split("T")[0]}.xlsx`);
    toast.success(t('shipment.exportedRows').replace('{0}', String(rows.length)));
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Block 1: Days until shipment */}
        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Package className="h-5 w-5 text-primary" />
              {t('shipment.daysUntil')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Label htmlFor="daysUntilShipment">{t('shipment.daysCount')}</Label>
              <Input
                id="daysUntilShipment"
                type="number"
                min={1}
                value={daysUntilShipment}
                onChange={(e) => setDaysUntilShipment(Number(e.target.value))}
                className="max-w-[200px]"
              />
              <p className="text-sm text-muted-foreground">
                {t('shipment.daysDescription')}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Block 2: Consider stock */}
        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Warehouse className="h-5 w-5 text-primary" />
              {t('shipment.considerStock')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <RadioGroup value={considerStock} onValueChange={setConsiderStock}>
                <div className="flex items-center gap-2">
                  <RadioGroupItem value="yes" id="stock-yes" />
                  <Label htmlFor="stock-yes" className="font-normal cursor-pointer">
                    {t('shipment.yes')}
                  </Label>
                </div>
                <div className="flex items-center gap-2">
                  <RadioGroupItem value="no" id="stock-no" />
                  <Label htmlFor="stock-no" className="font-normal cursor-pointer">
                    {t('shipment.no')}
                  </Label>
                </div>
              </RadioGroup>
              <Button
                type="button"
                className="w-full"
                onClick={handleCalculate}
                disabled={calculateLoading}
              >
                {calculateLoading ? t('shipment.calculating') : t('shipment.calculate')}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Рекомендации по отгрузке: left-out-report_old, Оборачиваемость < 60 */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <CardTitle>{t('shipment.recommendations')}</CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={handleExportXLSX}
            disabled={items.length === 0}
          >
            <Download className="w-4 h-4 mr-2" />
            {t('shipment.exportXLSX')}
          </Button>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow className="bg-violet-50/80 dark:bg-violet-950/30 border-border">
                  <TableHead className="bg-violet-50/80 dark:bg-violet-950/30">{t('shipment.product')}</TableHead>
                  <TableHead className="bg-violet-50/80 dark:bg-violet-950/30">{t('shipment.article')}</TableHead>
                  <TableHead className="bg-violet-50/80 dark:bg-violet-950/30">{t('product.barcode')}</TableHead>
                  <TableHead className="text-center whitespace-nowrap bg-violet-50/80 dark:bg-violet-950/30">{t('shipment.inStock')}</TableHead>
                  <TableHead className="text-center bg-violet-50/80 dark:bg-violet-950/30">
                    {t('shipment.salesPerDay')}
                  </TableHead>
                  <TableHead className="text-center bg-violet-50/80 dark:bg-violet-950/30">
                    {t('shipment.recommendedQty')}
                  </TableHead>
                  <TableHead className="text-center bg-violet-50/80 dark:bg-violet-950/30">
                    {t('shipment.plannedToShip')}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                      {t('expense.loading')}
                    </TableCell>
                  </TableRow>
                ) : error ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-destructive py-8">
                      {t('report.loadError')}
                    </TableCell>
                  </TableRow>
                ) : items.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                      {t('shipment.noDataHint')}
                    </TableCell>
                  </TableRow>
                ) : (
                  items.map((row, idx) => {
                    const key = rowKey(row);
                    const recommendedDisplay =
                      key && calculatedRecommendedByKey[key] !== undefined
                        ? String(calculatedRecommendedByKey[key])
                        : row.recommended_qty;
                    return (
                      <TableRow key={idx}>
                        <TableCell className="font-medium">{row.product_name ?? "—"}</TableCell>
                        <TableCell>{row.sku ?? "—"}</TableCell>
                        <TableCell className="font-mono text-sm">{row.barcode ?? "—"}</TableCell>
                        <TableCell className="text-center">{row.stock ?? "—"}</TableCell>
                        <TableCell className="text-center">{row.sales_per_day ?? "—"}</TableCell>
                        <TableCell className="text-center font-bold text-purple-600 dark:text-purple-400">
                          {recommendedDisplay}
                        </TableCell>
                        <TableCell className="text-center">{row.to_ship ?? "—"}</TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
