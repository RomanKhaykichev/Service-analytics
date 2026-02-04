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
import { Package, Calculator, Warehouse } from "lucide-react";
import { useShipmentRecommendations } from "@/hooks/useShipmentRecommendations";

interface ShipmentViewProps {
  /** Фильтр по магазину (seller-storage); фильтрует таблицу через fact_storage_snapshot по баркодам */
  shop?: string | null;
}

export function ShipmentView({ shop }: ShipmentViewProps) {
  const [daysUntilShipment, setDaysUntilShipment] = useState<number>(7);
  const [daysForCalculation, setDaysForCalculation] = useState<number>(30);
  const [considerStock, setConsiderStock] = useState<string>("yes");

  const { data, isLoading, error } = useShipmentRecommendations(shop);
  const items = data?.items ?? [];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
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

        {/* Block 2: Days for data calculation */}
        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Calculator className="h-5 w-5 text-primary" />
              Дней расчёта данных
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Label htmlFor="daysForCalculation">Количество дней</Label>
              <Input
                id="daysForCalculation"
                type="number"
                min={1}
                value={daysForCalculation}
                onChange={(e) => setDaysForCalculation(Number(e.target.value))}
                className="max-w-[200px]"
              />
              <p className="text-sm text-muted-foreground">
                Укажите период для расчёта средних показателей продаж
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Block 3: Consider stock */}
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
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="yes" id="stock-yes" />
                  <Label htmlFor="stock-yes">Да</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="no" id="stock-no" />
                  <Label htmlFor="stock-no">Нет</Label>
                </div>
              </RadioGroup>
              <Button type="button" className="w-full" disabled>
                Рассчитать
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
                <TableRow>
                  <TableHead>Товар</TableHead>
                  <TableHead>Артикул</TableHead>
                  <TableHead>Штрихкод</TableHead>
                  <TableHead className="text-center whitespace-nowrap">На складе</TableHead>
                  <TableHead className="text-center">
                    Продаж
                    <br />
                    в день
                  </TableHead>
                  <TableHead className="text-center">
                    Рекомендуемое
                    <br />
                    кол-во
                  </TableHead>
                  <TableHead className="text-center">
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
                  items.map((row, idx) => (
                    <TableRow key={idx}>
                      <TableCell className="font-medium">{row.product_name ?? "—"}</TableCell>
                      <TableCell>{row.sku ?? "—"}</TableCell>
                      <TableCell className="font-mono text-sm">{row.barcode ?? "—"}</TableCell>
                      <TableCell className="text-center">{row.stock ?? "—"}</TableCell>
                      <TableCell className="text-center">{row.sales_per_day ?? "—"}</TableCell>
                      <TableCell className="text-center">{row.recommended_qty}</TableCell>
                      <TableCell className="text-center">{row.to_ship ?? "—"}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
