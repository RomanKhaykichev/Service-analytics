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
import { Package, Warehouse } from "lucide-react";
import { useShipmentRecommendations } from "@/hooks/useShipmentRecommendations";
import type { ShipmentRecommendationItem } from "@/hooks/useShipmentRecommendations";
import { apiGet } from "@/lib/api";

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

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Block 1: Days until shipment */}
        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Package className="h-5 w-5 text-primary" />
              Дней до отгрузки
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Label htmlFor="daysUntilShipment">Количество дней</Label>
              <Input
                id="daysUntilShipment"
                type="number"
                min={1}
                value={daysUntilShipment}
                onChange={(e) => setDaysUntilShipment(Number(e.target.value))}
                className="max-w-[200px]"
              />
              <p className="text-sm text-muted-foreground">
                Укажите через сколько дней планируется отгрузка товара начиная с даты выгрузки последнего отчета
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Block 2: Consider stock */}
        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Warehouse className="h-5 w-5 text-primary" />
              Учитывать остатки на складах
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <RadioGroup value={considerStock} onValueChange={setConsiderStock}>
                <div className="flex items-center gap-2">
                  <RadioGroupItem value="yes" id="stock-yes" />
                  <Label htmlFor="stock-yes" className="font-normal cursor-pointer">
                    Да
                  </Label>
                </div>
                <div className="flex items-center gap-2">
                  <RadioGroupItem value="no" id="stock-no" />
                  <Label htmlFor="stock-no" className="font-normal cursor-pointer">
                    Нет
                  </Label>
                </div>
              </RadioGroup>
              <Button
                type="button"
                className="w-full"
                onClick={handleCalculate}
                disabled={calculateLoading}
              >
                {calculateLoading ? "Расчёт…" : "Рассчитать"}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Рекомендации по отгрузке: left-out-report_old, Оборачиваемость < 60 */}
      <Card>
        <CardHeader>
          <CardTitle>Рекомендации по отгрузке</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow className="bg-violet-50/80 dark:bg-violet-950/30 border-border">
                  <TableHead className="bg-violet-50/80 dark:bg-violet-950/30">Товар</TableHead>
                  <TableHead className="bg-violet-50/80 dark:bg-violet-950/30">Артикул</TableHead>
                  <TableHead className="bg-violet-50/80 dark:bg-violet-950/30">Штрихкод</TableHead>
                  <TableHead className="text-center whitespace-nowrap bg-violet-50/80 dark:bg-violet-950/30">На складе</TableHead>
                  <TableHead className="text-center bg-violet-50/80 dark:bg-violet-950/30">
                    Продаж
                    <br />
                    в день
                  </TableHead>
                  <TableHead className="text-center bg-violet-50/80 dark:bg-violet-950/30">
                    Рекомендуемое
                    <br />
                    кол-во
                  </TableHead>
                  <TableHead className="text-center bg-violet-50/80 dark:bg-violet-950/30">
                    Запланировано
                    <br />
                    к отгрузке
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                      Загрузка…
                    </TableCell>
                  </TableRow>
                ) : error ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-destructive py-8">
                      Ошибка загрузки данных
                    </TableCell>
                  </TableRow>
                ) : items.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                      Нет данных. Загрузите отчёт «Остатки (старый)» (left-out-report_old) с колонкой Оборачиваемость &lt; 60.
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
