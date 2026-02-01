import { useState, useEffect } from "react";
import { format } from "date-fns";
import { ru } from "date-fns/locale";
import { Plus, ArrowUpDown, Info, CalendarIcon, Trash2, Edit } from "lucide-react";
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
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
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
import { apiGet, apiPost, apiPut, apiDelete, buildQueryParams } from "@/lib/api";
import { useShops } from "@/hooks/useShops";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

interface ExtraExpense {
  id: number;
  expense_date: string;
  amount_sum: number;
  shop_id: string | null;
  shop_name: string | null;
  category: string | null;
  comment: string | null;
  created_at: string;
  updated_at: string;
}

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

interface ExtraExpensesResponse {
  expenses: ExtraExpense[];
  total: number;
}

interface ExpensesViewProps {
  periodCode?: string;
  shop?: string | null;
}

export function ExpensesView({ periodCode = "30d", shop = null }: ExpensesViewProps) {
  const { shops, loading: shopsLoading } = useShops();
  const queryClient = useQueryClient();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingExpense, setEditingExpense] = useState<ExtraExpense | null>(null);
  const [sortColumn, setSortColumn] = useState<keyof ExtraExpense | null>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const [calendarOpen, setCalendarOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [toDelete, setToDelete] = useState<ExtraExpense | null>(null);

  // Form state
  const [newExpense, setNewExpense] = useState({
    date: new Date(),
    type: "",
    amount: "",
    shop_id: "",
    comment: "",
  });

  // Load expenses from API (filter by shop name when selected)
  const { data: expensesData, isLoading: expensesLoading, error: expensesError } = useQuery({
    queryKey: ['extraExpenses', periodCode, shop],
    queryFn: async () => {
      try {
        const params = buildQueryParams({ period: periodCode, shop });
        return await apiGet<ExtraExpensesResponse>("/api/extra-expenses", params);
      } catch (error) {
        console.error("Failed to load expenses:", error);
        throw error;
      }
    },
    retry: 1, // Retry once on failure
    refetchOnWindowFocus: false, // Don't refetch on window focus
  });

  const expenses = expensesData?.expenses || [];

  // Create expense mutation
  const createMutation = useMutation({
    mutationFn: async (expense: {
      expense_date: string;
      amount_sum: number;
      shop_id?: string | null;
      category?: string | null;
      comment?: string | null;
    }) => {
      return await apiPost<ExtraExpense>("/api/extra-expenses", expense);
    },
    onSuccess: () => {
      // Invalidate and refetch expenses list to show new row immediately
      queryClient.invalidateQueries({ queryKey: ['extraExpenses'] });
      queryClient.refetchQueries({ queryKey: ['extraExpenses', periodCode, shop] });
      toast.success("Расход успешно добавлен");
      setIsDialogOpen(false);
      setEditingExpense(null);
      setNewExpense({
        date: new Date(),
        type: "",
        amount: "",
        shop_id: "",
        comment: "",
      });
    },
    onError: (error) => {
      const errorMessage = error instanceof Error 
        ? error.message 
        : "Ошибка при добавлении расхода";
      console.error("Create expense error:", error);
      toast.error(errorMessage);
    },
  });

  // Update expense mutation
  const updateMutation = useMutation({
    mutationFn: async ({ id, expense }: { id: number; expense: Partial<{
      expense_date?: string;
      amount_sum?: number;
      shop_id?: string | null;
      category?: string | null;
      comment?: string | null;
    }>}) => {
      return await apiPut<ExtraExpense>(`/api/extra-expenses/${id}`, expense);
    },
    onSuccess: () => {
      // Invalidate and refetch expenses list
      queryClient.invalidateQueries({ queryKey: ['extraExpenses'] });
      queryClient.refetchQueries({ queryKey: ['extraExpenses', periodCode, shop] });
      toast.success("Расход успешно обновлен");
      setIsDialogOpen(false);
      setEditingExpense(null);
      setNewExpense({
        date: new Date(),
        type: "",
        amount: "",
        shop_id: "",
        comment: "",
      });
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "Ошибка при обновлении расхода");
    },
  });

  // Delete expense mutation
  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      return await apiDelete(`/api/extra-expenses/${id}`);
    },
    onSuccess: () => {
      // Invalidate and refetch expenses list to remove deleted row immediately
      queryClient.invalidateQueries({ queryKey: ['extraExpenses'] });
      queryClient.refetchQueries({ queryKey: ['extraExpenses', periodCode, shop] });
      toast.success("Расход успешно удален");
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "Ошибка при удалении расхода");
    },
  });

  const handleSort = (column: keyof ExtraExpense) => {
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
    
    if (aValue === null || bValue === null) {
      if (aValue === null && bValue === null) return 0;
      return aValue === null ? 1 : -1;
    }
    
    if (typeof aValue === "number" && typeof bValue === "number") {
      return sortDirection === "asc" ? aValue - bValue : bValue - aValue;
    }
    
    if (typeof aValue === "string" && typeof bValue === "string") {
      // Handle date strings
      if (sortColumn === "expense_date" || sortColumn === "created_at" || sortColumn === "updated_at") {
        const aDate = new Date(aValue).getTime();
        const bDate = new Date(bValue).getTime();
        return sortDirection === "asc" ? aDate - bDate : bDate - aDate;
      }
      return sortDirection === "asc"
        ? aValue.localeCompare(bValue)
        : bValue.localeCompare(aValue);
    }
    
    return 0;
  });

  const handleSaveExpense = () => {
    if (!newExpense.type || !newExpense.amount) {
      toast.error("Заполните тип и сумму расхода");
      return;
    }

    const expenseData = {
      expense_date: format(newExpense.date, "yyyy-MM-dd"),
      amount_sum: Number(newExpense.amount),
      shop_id: newExpense.shop_id || null,
      category: newExpense.type,
      comment: newExpense.comment || null,
    };

    if (editingExpense) {
      updateMutation.mutate({ id: editingExpense.id, expense: expenseData });
    } else {
      createMutation.mutate(expenseData);
    }
  };

  const handleEdit = (expense: ExtraExpense) => {
    setEditingExpense(expense);
    setNewExpense({
      date: new Date(expense.expense_date),
      type: expense.category || "",
      amount: expense.amount_sum.toString(),
      shop_id: expense.shop_id || "",
      comment: expense.comment || "",
    });
    setIsDialogOpen(true);
  };

  const handleDeleteClick = (expense: ExtraExpense) => {
    setToDelete(expense);
    setDeleteOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!toDelete) return;
    try {
      await deleteMutation.mutateAsync(toDelete.id);
      setDeleteOpen(false);
      setToDelete(null);
    } catch (error) {
      // Ошибка уже обработана в onError deleteMutation (toast)
      // Диалог можно оставить открытым или закрыть - закрываем для UX
      setDeleteOpen(false);
      setToDelete(null);
    }
  };

  const handleDialogOpenChange = (open: boolean) => {
    try {
      setIsDialogOpen(open);
      if (open) {
        // Reset form when opening (for new expense)
        if (!editingExpense) {
          setNewExpense({
            date: new Date(),
            type: "",
            amount: "",
            shop_id: "",
            comment: "",
          });
        }
        // Close calendar when opening dialog
        setCalendarOpen(false);
      } else {
        // Reset form when closing
        setEditingExpense(null);
        setNewExpense({
          date: new Date(),
          type: "",
          amount: "",
          shop_id: "",
          comment: "",
        });
        // Close calendar when closing dialog
        setCalendarOpen(false);
      }
    } catch (error) {
      console.error("Error in handleDialogOpenChange:", error);
      // Fallback: ensure dialog state is consistent
      setIsDialogOpen(false);
      setCalendarOpen(false);
    }
  };

  const handleDialogClose = () => {
    try {
      setIsDialogOpen(false);
      setEditingExpense(null);
      setNewExpense({
        date: new Date(),
        type: "",
        amount: "",
        shop_id: "",
        comment: "",
      });
    } catch (error) {
      console.error("Error in handleDialogClose:", error);
      setIsDialogOpen(false);
    }
  };

  const SortableHeader = ({ column, children }: { column: keyof ExtraExpense; children: React.ReactNode }) => (
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
          <div className={cn(
            "overflow-x-auto",
            sortedExpenses.length > 10 && "max-h-[500px] overflow-y-auto"
          )}>
            <Table>
              <TableHeader className="sticky top-0 bg-background z-10 [&_tr]:bg-background [&_th]:bg-background">
                <TableRow>
                  <SortableHeader column="expense_date">Дата</SortableHeader>
                  <SortableHeader column="category">Тип</SortableHeader>
                  <SortableHeader column="amount_sum">Сумма</SortableHeader>
                  <SortableHeader column="shop_name">Магазин</SortableHeader>
                  <TableHead>Комментарий</TableHead>
                  <TableHead className="w-[100px]">Действия</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {expensesLoading ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                      Загрузка...
                    </TableCell>
                  </TableRow>
                ) : sortedExpenses.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                      Нет добавленных расходов
                    </TableCell>
                  </TableRow>
                ) : (
                  sortedExpenses.map((expense) => (
                    <TableRow key={expense.id}>
                      <TableCell>
                        {format(new Date(expense.expense_date), "dd.MM.yyyy", { locale: ru })}
                      </TableCell>
                      <TableCell>
                        <span className="px-2 py-1 rounded-md bg-muted text-sm">
                          {expense.category || "—"}
                        </span>
                      </TableCell>
                      <TableCell className="font-medium text-destructive">
                        -{expense.amount_sum.toLocaleString("ru-RU")} сум
                      </TableCell>
                      <TableCell>{expense.shop_name || "—"}</TableCell>
                      <TableCell className="max-w-[200px] truncate">
                        {expense.comment || "—"}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => handleEdit(expense)}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-destructive hover:text-destructive"
                            onClick={() => handleDeleteClick(expense)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {/* Add Expense Button */}
          <div className="p-4 border-t">
            <Dialog open={isDialogOpen} onOpenChange={handleDialogOpenChange}>
              <DialogTrigger asChild>
                <Button 
                  className="w-full sm:w-auto" 
                  type="button"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Добавить расход
                </Button>
              </DialogTrigger>
              <DialogContent 
                className="sm:max-w-[425px]"
                onInteractOutside={(e) => {
                  // Prevent closing dialog when clicking on calendar popover
                  const target = e.target as HTMLElement;
                  if (target.closest("[data-datepicker-popover]")) {
                    e.preventDefault();
                  }
                }}
              >
                <DialogHeader>
                  <DialogTitle>{editingExpense ? "Редактировать расход" : "Добавить расход"}</DialogTitle>
                  <DialogDescription>
                    {editingExpense ? "Измените данные расхода" : "Заполните форму для добавления нового расхода"}
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  {/* Date */}
                  <div className="grid gap-2">
                    <Label>Дата</Label>
                    <Popover 
                      open={calendarOpen} 
                      onOpenChange={setCalendarOpen}
                    >
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
                      <PopoverContent 
                        className="w-auto p-0" 
                        align="start"
                        data-datepicker-popover
                      >
                        <Calendar
                          mode="single"
                          selected={newExpense.date}
                          onSelect={(date) => {
                            if (!date) return;
                            setNewExpense({ ...newExpense, date: date });
                            setCalendarOpen(false); // КЛЮЧЕВО: закрыть календарь после выбора даты
                          }}
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
                    <Label>Сумма</Label>
                    <Input
                      type="number"
                      placeholder="0"
                      value={newExpense.amount}
                      onChange={(e) =>
                        setNewExpense({ ...newExpense, amount: e.target.value })
                      }
                    />
                  </div>

                  {/* Shop */}
                  <div className="grid gap-2">
                    <Label>Магазин</Label>
                    <Select
                      value={newExpense.shop_id}
                      onValueChange={(value) =>
                        setNewExpense({ ...newExpense, shop_id: value || "" })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Выберите магазин (опционально)" />
                      </SelectTrigger>
                      <SelectContent>
                        {shopsLoading ? (
                          <SelectItem value="" disabled>Загрузка...</SelectItem>
                        ) : shops.length === 0 ? (
                          <SelectItem value="" disabled>Нет доступных магазинов</SelectItem>
                        ) : (
                          <>
                            {shops.map((shop) => (
                              <SelectItem key={shop.shop_id} value={shop.shop_id}>
                                {shop.shop_name || shop.shop_id}
                              </SelectItem>
                            ))}
                          </>
                        )}
                      </SelectContent>
                    </Select>
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
                    onClick={handleDialogClose}
                    disabled={createMutation.isPending || updateMutation.isPending}
                  >
                    Отмена
                  </Button>
                  <Button 
                    onClick={handleSaveExpense}
                    disabled={createMutation.isPending || updateMutation.isPending}
                  >
                    {editingExpense ? "Сохранить" : "Добавить"}
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Вы уверены, что хотите удалить этот расход?</AlertDialogTitle>
            <AlertDialogDescription>
              Это действие нельзя отменить.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => {
              setDeleteOpen(false);
              setToDelete(null);
            }}>
              Нет
            </AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={handleConfirmDelete}
              disabled={deleteMutation.isPending}
            >
              Да
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
