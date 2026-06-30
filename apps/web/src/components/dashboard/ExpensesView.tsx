import { useState, useEffect } from "react";
import { format } from "date-fns";
import { ru } from "date-fns/locale";
import { Plus, ArrowUpDown, CalendarIcon, Trash2, Edit } from "lucide-react";
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
import { useLanguage } from "@/contexts/LanguageContext";
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
import { useStorageShops } from "@/hooks/useStorageShops";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface ExtraExpense {
  id: number;
  expense_date: string;
  amount_sum: number;
  shop_id: string | null;
  shop_name: string | null;
  category: string | null;
  name: string | null;
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

const expenseTypeOptions: { value: string; labelKey: string }[] = [
  { value: "Самовыкуп", labelKey: "expense.typeSelfBuy" },
  { value: "Зарплата", labelKey: "expense.typeSalary" },
  { value: "Внешняя реклама", labelKey: "expense.typeExternalAds" },
  { value: "Своя логистика", labelKey: "expense.typeOwnLogistics" },
  { value: "Упаковка", labelKey: "expense.typePackaging" },
  { value: "Аренда", labelKey: "expense.typeRent" },
  { value: "Прочее", labelKey: "expense.typeOther" },
];

interface ExtraExpensesResponse {
  expenses: ExtraExpense[];
  total: number;
}

interface ProductNamesResponse {
  names: string[];
}

interface ExpensesViewProps {
  /** Не передавать — вкладка Доп. расходы показывает все данные без фильтров по дате и магазину */
  dateFrom?: string;
  dateTo?: string;
  shop?: string | null;
}

export function ExpensesView({ dateFrom, dateTo, shop = null }: ExpensesViewProps) {
  const { t } = useLanguage();
  const { shops, loading: shopsLoading } = useStorageShops();
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
    name: "",
    comment: "",
  });

  // Format number with spaces as thousands separator
  const formatAmount = (value: string): string => {
    // Remove all non-digit characters except decimal point
    const numericValue = value.replace(/[^\d.]/g, '');
    if (!numericValue) return '';
    
    // Split by decimal point if exists
    const parts = numericValue.split('.');
    const integerPart = parts[0];
    const decimalPart = parts[1];
    
    // Add spaces every 3 digits from right to left
    const formattedInteger = integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    
    // Combine with decimal part if exists
    return decimalPart !== undefined ? `${formattedInteger}.${decimalPart}` : formattedInteger;
  };

  // Parse formatted amount back to number string (remove spaces)
  const parseAmount = (value: string): string => {
    return value.replace(/\s/g, '');
  };

  const noFilters = dateFrom == null || dateTo == null;
  const extraExpensesQueryKey = ['extraExpenses', noFilters ? 'all' : dateFrom, noFilters ? null : dateTo, shop];

  const { data: expensesData, isLoading: expensesLoading, error: expensesError } = useQuery({
    queryKey: extraExpensesQueryKey,
    queryFn: async () => {
      const params = noFilters
        ? { period: "all" }
        : buildQueryParams({ date_from: dateFrom, date_to: dateTo, shop });
      const response = await apiGet<ExtraExpensesResponse>("/api/extra-expenses", params);
      console.log("Fetched expenses:", response);
      console.log("First expense name:", response?.expenses?.[0]?.name);
      return response;
    },
    enabled: true,
    retry: 1,
    refetchOnWindowFocus: false,
  });

  const expenses = expensesData?.expenses || [];
  console.log("Current expenses list, first expense:", expenses[0]);
  console.log("First expense name:", expenses[0]?.name);

  // Ensure name column exists in database on component mount
  useEffect(() => {
    const ensureNameColumn = async () => {
      try {
        const result = await apiGet<{ status: string; message: string; has_name?: boolean }>("/api/extra-expenses/ensure-name-column");
        console.log("Name column check result:", result);
        if (result.status === "created") {
          // Refetch expenses after column creation
          queryClient.invalidateQueries({ queryKey: ['extraExpenses'] });
        }
      } catch (error) {
        console.error("Failed to ensure name column:", error);
      }
    };
    ensureNameColumn();
  }, [queryClient]);

  // Fetch product names for autocomplete - filter by shop_id if selected
  const { data: productNamesData } = useQuery({
    queryKey: ['productNames', newExpense.shop_id || null],
    queryFn: async () => {
      const params = newExpense.shop_id && newExpense.shop_id.trim() && newExpense.shop_id !== "__none__"
        ? { shop_id: newExpense.shop_id }
        : {};
      console.log("Fetching product names with params:", params);
      const result = await apiGet<ProductNamesResponse>("/api/extra-expenses/product-names", params);
      console.log("Product names result:", result);
      return result;
    },
    enabled: true,
    retry: 1,
    refetchOnWindowFocus: false,
  });

  const productNames = productNamesData?.names || [];

  // Create expense mutation
  const createMutation = useMutation({
    mutationFn: async (expense: {
      expense_date: string;
      amount_sum: number;
      shop?: string | null;
      category?: string | null;
      name?: string | null;
      comment?: string | null;
    }) => {
      return await apiPost<ExtraExpense>("/api/extra-expenses", expense);
    },
    onSuccess: (data) => {
      console.log("Expense created successfully, response:", data);
      console.log("Created expense name:", data?.name);
      // Invalidate and refetch expenses list to show new row immediately
      queryClient.invalidateQueries({ queryKey: ['extraExpenses'] });
      queryClient.refetchQueries({ queryKey: extraExpensesQueryKey });
      // Чтобы на вкладках Сводка и По месячно метрики (в т.ч. доп. расходы) обновились без перезагрузки
      queryClient.invalidateQueries({ queryKey: ['kpiSummary'] });
      queryClient.invalidateQueries({ queryKey: ['kpiMonthly'] });
      toast.success("Расход успешно добавлен");
      setIsDialogOpen(false);
      setEditingExpense(null);
      setNewExpense({
        date: new Date(),
        type: "",
        amount: "",
        shop_id: "",
        name: "",
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
      name?: string | null;
      comment?: string | null;
    }>}) => {
      return await apiPut<ExtraExpense>(`/api/extra-expenses/${id}`, expense);
    },
    onSuccess: () => {
      // Invalidate and refetch expenses list
      queryClient.invalidateQueries({ queryKey: ['extraExpenses'] });
      queryClient.refetchQueries({ queryKey: extraExpensesQueryKey });
      queryClient.invalidateQueries({ queryKey: ['kpiSummary'] });
      queryClient.invalidateQueries({ queryKey: ['kpiMonthly'] });
      toast.success("Расход успешно обновлен");
      setIsDialogOpen(false);
      setEditingExpense(null);
      setNewExpense({
        date: new Date(),
        type: "",
        amount: "",
        shop_id: "",
        name: "",
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
      queryClient.refetchQueries({ queryKey: extraExpensesQueryKey });
      queryClient.invalidateQueries({ queryKey: ['kpiSummary'] });
      queryClient.invalidateQueries({ queryKey: ['kpiMonthly'] });
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

    console.log("Saving expense, name value:", newExpense.name);

    if (editingExpense) {
      const expenseData = {
        expense_date: format(newExpense.date, "yyyy-MM-dd"),
        amount_sum: Number(parseAmount(newExpense.amount)) || 0,
        shop_id: newExpense.shop_id || null,
        category: newExpense.type,
        name: newExpense.name && newExpense.name.trim() ? newExpense.name.trim() : null,
        comment: newExpense.comment || null,
      };
      console.log("Update expense data:", expenseData);
      updateMutation.mutate({ id: editingExpense.id, expense: expenseData });
    } else {
      // При создании отправляем shop (название из seller-storage); бэкенд резолвит в shop_id
      const expenseData = {
        expense_date: format(newExpense.date, "yyyy-MM-dd"),
        amount_sum: Number(parseAmount(newExpense.amount)) || 0,
        shop: newExpense.shop_id || null,
        category: newExpense.type,
        name: newExpense.name && newExpense.name.trim() ? newExpense.name.trim() : null,
        comment: newExpense.comment || null,
      };
      console.log("Create expense data:", expenseData);
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
      name: expense.name || "",
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
        name: "",
        comment: "",
      });
    } catch (error) {
      console.error("Error in handleDialogClose:", error);
      setIsDialogOpen(false);
    }
  };

  const SortableHeader = ({ column, children }: { column: keyof ExtraExpense; children: React.ReactNode }) => (
    <TableHead
      className="cursor-pointer bg-violet-50/80 dark:bg-violet-950/30 hover:bg-violet-100/80 dark:hover:bg-violet-900/40 transition-colors"
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
      {/* Expenses Table */}
      <Card>
        <CardContent className="p-0">
          <div className={cn(
            "overflow-x-auto",
            sortedExpenses.length > 10 && "max-h-[500px] overflow-y-auto"
          )}>
            <Table>
              <TableHeader className="sticky top-0 z-10 [&_tr]:bg-violet-50/80 [&_tr]:dark:bg-violet-950/30 [&_th]:bg-violet-50/80 [&_th]:dark:bg-violet-950/30">
                <TableRow className="bg-violet-50/80 dark:bg-violet-950/30 border-border">
                  <SortableHeader column="expense_date" className="w-auto whitespace-nowrap">{t('expense.date')}</SortableHeader>
                  <SortableHeader column="category" className="w-auto whitespace-nowrap">{t('expense.type')}</SortableHeader>
                  <SortableHeader column="amount_sum" className="w-auto whitespace-nowrap">{t('expense.amount')}</SortableHeader>
                  <SortableHeader column="name">{t('table.productName')}</SortableHeader>
                  <SortableHeader column="shop_name">{t('table.shop')}</SortableHeader>
                  <TableHead className="bg-violet-50/80 dark:bg-violet-950/30">{t('product.comment')}</TableHead>
                  <TableHead className="w-[100px] bg-violet-50/80 dark:bg-violet-950/30">{t('expense.actions')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {expensesLoading ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                      {t('expense.loading')}
                    </TableCell>
                  </TableRow>
                ) : sortedExpenses.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                      {t('expense.noExpensesAdded')}
                    </TableCell>
                  </TableRow>
                ) : (
                  sortedExpenses.map((expense) => (
                    <TableRow key={expense.id}>
                      <TableCell>
                        {format(new Date(expense.expense_date), "dd.MM.yyyy", { locale: ru })}
                      </TableCell>
                      <TableCell className="whitespace-nowrap">
                        <span className="px-2 py-1 rounded-md bg-muted text-sm">
                          {expense.category || "—"}
                        </span>
                      </TableCell>
                      <TableCell className="font-medium text-destructive whitespace-nowrap">
                        -{expense.amount_sum.toLocaleString("ru-RU")}
                      </TableCell>
                      <TableCell className="break-words">
                        {expense.name && expense.name.trim() ? expense.name : "—"}
                      </TableCell>
                      <TableCell>
                        {expense.shop_name && expense.shop_name.trim() ? expense.shop_name : "—"}
                      </TableCell>
                      <TableCell className="max-w-[200px]">
                        {expense.comment && expense.comment.trim() ? (
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <div className="truncate cursor-help">
                                  {expense.comment}
                                </div>
                              </TooltipTrigger>
                              <TooltipContent className="max-w-[400px] break-words">
                                <p>{expense.comment}</p>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        ) : (
                          "—"
                        )}
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
                  {t('expense.addExpense')}
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
                  <DialogTitle>{editingExpense ? t('expense.editExpense') : t('expense.addExpense')}</DialogTitle>
                  <DialogDescription>
                    {editingExpense ? t('expense.editDesc') : t('expense.addDesc')}
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  {/* Date */}
                  <div className="grid gap-2">
                    <Label>{t('expense.date')}</Label>
                    <Input
                      type="date"
                      value={newExpense.date ? format(newExpense.date, "yyyy-MM-dd") : ""}
                      onChange={(e) => {
                        const value = e.target.value;
                        if (!value) return;
                        const nextDate = new Date(value);
                        if (Number.isNaN(nextDate.getTime())) return;
                        setNewExpense({ ...newExpense, date: nextDate });
                      }}
                      className="h-9"
                    />
                  </div>

                  {/* Type */}
                  <div className="grid gap-2">
                    <Label>{t('expense.typeLabel')}</Label>
                    <Select
                      value={newExpense.type}
                      onValueChange={(value) =>
                        setNewExpense({ ...newExpense, type: value })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder={t('expense.selectType')} />
                      </SelectTrigger>
                      <SelectContent>
                        {expenseTypeOptions.map((opt) => (
                          <SelectItem key={opt.value} value={opt.value}>
                            {t(opt.labelKey)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Amount */}
                  <div className="grid gap-2">
                    <Label>{t('expense.amount')}</Label>
                    <Input
                      type="text"
                      placeholder="0"
                      value={formatAmount(newExpense.amount)}
                      onChange={(e) => {
                        const rawValue = parseAmount(e.target.value);
                        // Allow only numbers and decimal point
                        if (rawValue === '' || /^\d*\.?\d*$/.test(rawValue)) {
                          setNewExpense({ ...newExpense, amount: rawValue });
                        }
                      }}
                    />
                  </div>

                  {/* Shop: список из seller-storage (колонка «Магазин»); при редактировании добавляем текущий магазин в опции */}
                  <div className="grid gap-2">
                    <Label>{t('table.shop')}</Label>
                    <Select
                      value={
                        shopsLoading
                          ? "__loading__"
                          : (newExpense.shop_id === "" || newExpense.shop_id == null ? "__none__" : newExpense.shop_id)
                      }
                      onValueChange={(value) => {
                        if (value === "__loading__" || value === "__empty__") return;
                        setNewExpense({ ...newExpense, shop_id: value === "__none__" ? "" : value });
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder={t('expense.selectShopOptional')} />
                      </SelectTrigger>
                      <SelectContent>
                        {shopsLoading ? (
                          <SelectItem value="__loading__" disabled>{t('expense.loading')}</SelectItem>
                        ) : (
                          <>
                            <SelectItem value="__none__">{t('expense.notSelected')}</SelectItem>
                            {(shops ?? []).filter((s) => s?.shop_id != null && String(s.shop_id).trim() !== "").map((shop) => (
                              <SelectItem key={String(shop.shop_id)} value={String(shop.shop_id)}>
                                {shop.shop_name ?? shop.shop_id ?? ""}
                              </SelectItem>
                            ))}
                            {editingExpense?.shop_id && !(shops ?? []).some((s) => s?.shop_id === editingExpense?.shop_id) && (
                              <SelectItem value={String(editingExpense.shop_id)}>
                                {editingExpense.shop_name ?? editingExpense.shop_id ?? ""}
                              </SelectItem>
                            )}
                            {(shops ?? []).length === 0 && !editingExpense?.shop_id ? (
                              <SelectItem value="__empty__" disabled>{t('expense.noShopsAvailable')}</SelectItem>
                            ) : null}
                          </>
                        )}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Name: product name from left-out-report_old with dropdown selection */}
                  <div className="grid gap-2">
                    <Label>{t('table.productName')}</Label>
                    <Select
                      value={newExpense.name === "" || newExpense.name == null ? "__none__" : newExpense.name}
                      onValueChange={(value) => {
                        if (value === "__loading__" || value === "__empty__") return;
                        setNewExpense({ ...newExpense, name: value === "__none__" ? "" : value });
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder={t('expense.selectNameOptional')} />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="__none__">{t('expense.notSelectedItem')}</SelectItem>
                        {productNames.length > 0 ? (
                          productNames.map((name) => (
                            <SelectItem key={name} value={name}>
                              {name}
                            </SelectItem>
                          ))
                        ) : (
                          <SelectItem value="__empty__" disabled>
                            {t('expense.noNamesAvailable')}
                          </SelectItem>
                        )}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Comment */}
                  <div className="grid gap-2">
                    <Label>{t('product.comment')}</Label>
                    <Textarea
                      placeholder={t('expense.commentOptional')}
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
                    {t('action.cancel')}
                  </Button>
                  <Button 
                    onClick={handleSaveExpense}
                    disabled={createMutation.isPending || updateMutation.isPending}
                  >
                    {editingExpense ? t('expense.save') : t('expense.add')}
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
