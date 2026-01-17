import { useState } from "react";
import { format } from "date-fns";
import { ru } from "date-fns/locale";
import { Plus, ArrowUpDown, Info, CalendarIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Calendar } from "@/components/ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";

interface Expense {
  id: string;
  date: Date;
  type: string;
  amount: number;
  store: string;
  product: string;
  comment: string;
}

const expenseTypes = [
  "Самовыкуп",
  "Зарплата",
  "Внешняя реклама",
  "Своя логистика",
  "Упаковка",
  "Аренда",
  "Прочее",
];

const stores = ["Все магазины", "Магазин 1", "Магазин 2", "Магазин 3"];

// Mock data
const mockExpenses: Expense[] = [
  {
    id: "1",
    date: new Date(2024, 11, 15),
    type: "Самовыкуп",
    amount: 15000,
    store: "Магазин 1",
    product: "Футболка белая",
    comment: "Тестовый заказ",
  },
  {
    id: "2",
    date: new Date(2024, 11, 10),
    type: "Внешняя реклама",
    amount: 50000,
    store: "Все магазины",
    product: "",
    comment: "Instagram реклама",
  },
  {
    id: "3",
    date: new Date(2024, 11, 5),
    type: "Зарплата",
    amount: 80000,
    store: "Все магазины",
    product: "",
    comment: "Менеджер по продажам",
  },
];

export function ExpensesView() {
  const [expenses, setExpenses] = useState<Expense[]>(mockExpenses);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [sortColumn, setSortColumn] = useState<keyof Expense | null>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  // Form state
  const [newExpense, setNewExpense] = useState({
    date: new Date(),
    type: "",
    amount: "",
    store: "",
    product: "",
    comment: "",
  });

  const handleSort = (column: keyof Expense) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortColumn(column);
      setSortDirection("desc");
    }
  };

  const sortedExpenses = [...expenses].sort((a, b) => {
    if (!sortColumn) return 0;
    
    const aValue = a[sortColumn];
    const bValue = b[sortColumn];
    
    if (aValue instanceof Date && bValue instanceof Date) {
      return sortDirection === "asc" 
        ? aValue.getTime() - bValue.getTime()
        : bValue.getTime() - aValue.getTime();
    }
    
    if (typeof aValue === "number" && typeof bValue === "number") {
      return sortDirection === "asc" ? aValue - bValue : bValue - aValue;
    }
    
    if (typeof aValue === "string" && typeof bValue === "string") {
      return sortDirection === "asc"
        ? aValue.localeCompare(bValue)
        : bValue.localeCompare(aValue);
    }
    
    return 0;
  });

  const handleAddExpense = () => {
    if (!newExpense.type || !newExpense.amount) return;

    const expense: Expense = {
      id: Date.now().toString(),
      date: newExpense.date,
      type: newExpense.type,
      amount: Number(newExpense.amount),
      store: newExpense.store || "Все магазины",
      product: newExpense.product,
      comment: newExpense.comment,
    };

    setExpenses([expense, ...expenses]);
    setNewExpense({
      date: new Date(),
      type: "",
      amount: "",
      store: "",
      product: "",
      comment: "",
    });
    setIsDialogOpen(false);
  };

  const SortableHeader = ({ column, children }: { column: keyof Expense; children: React.ReactNode }) => (
    <TableHead
      className="cursor-pointer hover:bg-muted/50 transition-colors"
      onClick={() => handleSort(column)}
    >
      <div className="flex items-center gap-1">
        {children}
        <ArrowUpDown className="h-3 w-3 opacity-50" />
      </div>
    </TableHead>
  );

  return (
    <div className="space-y-6">
      {/* Info Block */}
      <Card className="bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-800">
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-full bg-blue-100 dark:bg-blue-900">
              <Info className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div className="space-y-2">
              <h3 className="font-semibold text-foreground">Как это работает?</h3>
              <ul className="text-sm text-muted-foreground space-y-1.5">
                <li className="flex items-start gap-2">
                  <span className="text-blue-600 dark:text-blue-400">•</span>
                  <span>Здесь можно вручную добавить любые дополнительные расходы, которые не передаются по выгрузке в отчетах или через API из маркетплейса</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-blue-600 dark:text-blue-400">•</span>
                  <span>Примеры расходов - самовыкупы, зарплата, внешняя реклама, своя логистика и т.д.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-blue-600 dark:text-blue-400">•</span>
                  <span>Расходы будут учитываться во всех отчетах с финансами для выбранной даты и магазина/товара (если указаны)</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-blue-600 dark:text-blue-400">•</span>
                  <span className="text-muted-foreground/80 italic">Если не указаны — расходы будут добавлены в месячный отчет в общем</span>
                </li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Expenses Table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <SortableHeader column="date">Дата</SortableHeader>
                  <SortableHeader column="type">Тип</SortableHeader>
                  <SortableHeader column="amount">Сумма</SortableHeader>
                  <SortableHeader column="store">Магазин</SortableHeader>
                  <SortableHeader column="product">Товар</SortableHeader>
                  <SortableHeader column="comment">Комментарий</SortableHeader>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedExpenses.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                      Нет добавленных расходов
                    </TableCell>
                  </TableRow>
                ) : (
                  sortedExpenses.map((expense) => (
                    <TableRow key={expense.id}>
                      <TableCell>
                        {format(expense.date, "dd.MM.yyyy", { locale: ru })}
                      </TableCell>
                      <TableCell>
                        <span className="px-2 py-1 rounded-md bg-muted text-sm">
                          {expense.type}
                        </span>
                      </TableCell>
                      <TableCell className="font-medium text-destructive">
                        -{expense.amount.toLocaleString("ru-RU")} ₽
                      </TableCell>
                      <TableCell>{expense.store}</TableCell>
                      <TableCell>{expense.product || "—"}</TableCell>
                      <TableCell className="max-w-[200px] truncate">
                        {expense.comment || "—"}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {/* Add Expense Button */}
          <div className="p-4 border-t">
            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
              <DialogTrigger asChild>
                <Button className="w-full sm:w-auto">
                  <Plus className="h-4 w-4 mr-2" />
                  Добавить расход
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                  <DialogTitle>Добавить расход</DialogTitle>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  {/* Date */}
                  <div className="grid gap-2">
                    <Label>Дата</Label>
                    <Popover>
                      <PopoverTrigger asChild>
                        <Button
                          variant="outline"
                          className={cn(
                            "w-full justify-start text-left font-normal",
                            !newExpense.date && "text-muted-foreground"
                          )}
                        >
                          <CalendarIcon className="mr-2 h-4 w-4" />
                          {newExpense.date
                            ? format(newExpense.date, "dd.MM.yyyy", { locale: ru })
                            : "Выберите дату"}
                        </Button>
                      </PopoverTrigger>
                      <PopoverContent className="w-auto p-0" align="start">
                        <Calendar
                          mode="single"
                          selected={newExpense.date}
                          onSelect={(date) =>
                            setNewExpense({ ...newExpense, date: date || new Date() })
                          }
                          initialFocus
                          className="pointer-events-auto"
                        />
                      </PopoverContent>
                    </Popover>
                  </div>

                  {/* Type */}
                  <div className="grid gap-2">
                    <Label>Тип расхода</Label>
                    <Select
                      value={newExpense.type}
                      onValueChange={(value) =>
                        setNewExpense({ ...newExpense, type: value })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Выберите тип" />
                      </SelectTrigger>
                      <SelectContent>
                        {expenseTypes.map((type) => (
                          <SelectItem key={type} value={type}>
                            {type}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Amount */}
                  <div className="grid gap-2">
                    <Label>Сумма (₽)</Label>
                    <Input
                      type="number"
                      placeholder="0"
                      value={newExpense.amount}
                      onChange={(e) =>
                        setNewExpense({ ...newExpense, amount: e.target.value })
                      }
                    />
                  </div>

                  {/* Store */}
                  <div className="grid gap-2">
                    <Label>Магазин</Label>
                    <Select
                      value={newExpense.store}
                      onValueChange={(value) =>
                        setNewExpense({ ...newExpense, store: value })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Выберите магазин (опционально)" />
                      </SelectTrigger>
                      <SelectContent>
                        {stores.map((store) => (
                          <SelectItem key={store} value={store}>
                            {store}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Product */}
                  <div className="grid gap-2">
                    <Label>Товар</Label>
                    <Input
                      placeholder="Введите название товара (опционально)"
                      value={newExpense.product}
                      onChange={(e) =>
                        setNewExpense({ ...newExpense, product: e.target.value })
                      }
                    />
                  </div>

                  {/* Comment */}
                  <div className="grid gap-2">
                    <Label>Комментарий</Label>
                    <Textarea
                      placeholder="Добавьте комментарий (опционально)"
                      value={newExpense.comment}
                      onChange={(e) =>
                        setNewExpense({ ...newExpense, comment: e.target.value })
                      }
                    />
                  </div>
                </div>

                <div className="flex justify-end gap-2">
                  <Button
                    variant="outline"
                    onClick={() => setIsDialogOpen(false)}
                  >
                    Отмена
                  </Button>
                  <Button onClick={handleAddExpense}>Добавить</Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
