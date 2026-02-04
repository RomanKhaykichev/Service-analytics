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

// Mock data for the table
const mockProducts = [
  { id: 1, name: "Футболка базовая", article: "FT-001", barcode: "4680012345678", stock: 150, salesPerDay: 12, recommended: 84 },
  { id: 2, name: "Джинсы классические", article: "JN-002", barcode: "4680012345679", stock: 80, salesPerDay: 5, recommended: 35 },
  { id: 3, name: "Куртка зимняя", article: "KR-003", barcode: "4680012345680", stock: 45, salesPerDay: 3, recommended: 21 },
  { id: 4, name: "Кроссовки спортивные", article: "KS-004", barcode: "4680012345681", stock: 200, salesPerDay: 18, recommended: 126 },
  { id: 5, name: "Рубашка офисная", article: "RB-005", barcode: "4680012345682", stock: 60, salesPerDay: 4, recommended: 28 },
];

export function ShipmentView() {
  const [daysUntilShipment, setDaysUntilShipment] = useState<number>(7);
  const [daysForCalculation, setDaysForCalculation] = useState<number>(30);
  const [considerStock, setConsiderStock] = useState<string>("yes");
  const [calculatedData, setCalculatedData] = useState(mockProducts);

  const handleCalculate = () => {
    const updated = mockProducts.map(product => ({
      ...product,
      recommended: considerStock === "yes" 
        ? Math.max(0, (product.salesPerDay * daysUntilShipment) - product.stock)
        : product.salesPerDay * daysUntilShipment
    }));
    setCalculatedData(updated);
  };

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
              <Button onClick={handleCalculate} className="w-full">
                Рассчитать
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Shipment calculation table */}
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
                  <TableHead className="text-right">На складе</TableHead>
                  <TableHead className="text-right">Продаж в день</TableHead>
                  <TableHead className="text-right">Рекомендуемое кол-во</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {calculatedData.map((product) => (
                  <TableRow key={product.id}>
                    <TableCell className="font-medium">{product.name}</TableCell>
                    <TableCell>{product.article}</TableCell>
                    <TableCell className="font-mono text-sm">{product.barcode}</TableCell>
                    <TableCell className="text-right">{product.stock}</TableCell>
                    <TableCell className="text-right">{product.salesPerDay}</TableCell>
                    <TableCell className="text-right font-semibold text-primary">
                      {product.recommended}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
