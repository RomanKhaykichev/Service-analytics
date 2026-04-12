import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertCircle, Inbox, Shield, Trash2 } from "lucide-react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import { apiDelete, apiGet, apiPatch } from "@/lib/api";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

interface SupportTicketRow {
  id: string;
  user_id: string;
  email?: string | null;
  full_name?: string | null;
  subject: string;
  priority: string;
  category: string;
  description: string;
  created_at: string;
  resolved: boolean;
}

interface SupportTicketsResponse {
  tickets: SupportTicketRow[];
  total_count: number;
}

const PRIORITY_RU: Record<string, string> = {
  low: "Низкий",
  medium: "Средний",
  high: "Высокий",
  critical: "Критический",
};

const CATEGORY_RU: Record<string, string> = {
  technical: "Техническая",
  billing: "Оплата и тариф",
  feature: "Функции",
  data: "Данные и отчёты",
  other: "Другое",
};

function formatRuDate(iso: string) {
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

type StatusFilter = "all" | "open" | "closed";

export default function AdminAppeals() {
  const [accessDenied, setAccessDenied] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<SupportTicketsResponse | null>(null);
  const [busyTicketId, setBusyTicketId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");

  const setTicketResolved = useCallback(
    async (id: string, resolved: boolean) => {
      setBusyTicketId(id);
      try {
        await apiPatch<SupportTicketRow>(`/api/admin/support-tickets/${id}`, { resolved });
        setData((prev) => {
          if (!prev) return prev;
          if (statusFilter === "open" && resolved) {
            return {
              ...prev,
              tickets: prev.tickets.filter((t) => t.id !== id),
              total_count: Math.max(0, prev.total_count - 1),
            };
          }
          if (statusFilter === "closed" && !resolved) {
            return {
              ...prev,
              tickets: prev.tickets.filter((t) => t.id !== id),
              total_count: Math.max(0, prev.total_count - 1),
            };
          }
          return {
            ...prev,
            tickets: prev.tickets.map((t) => (t.id === id ? { ...t, resolved } : t)),
          };
        });
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        toast.error(msg || "Не удалось сохранить");
      } finally {
        setBusyTicketId(null);
      }
    },
    [statusFilter]
  );

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    setAccessDenied(false);
    try {
      const res = await apiGet<SupportTicketsResponse>("/api/admin/support-tickets", {
        page: 1,
        page_size: 200,
        status: statusFilter,
      });
      setData(res);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      if (msg.includes("403") || msg.includes("Admin")) {
        setAccessDenied(true);
      } else {
        setLoadError(msg);
      }
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  const executeDelete = async () => {
    if (!confirmDeleteId) return;
    setDeleteLoading(true);
    setDeletingId(confirmDeleteId);
    try {
      await apiDelete<{ ok: boolean }>(`/api/admin/support-tickets/${confirmDeleteId}`);
      setData((prev) =>
        prev
          ? {
              ...prev,
              tickets: prev.tickets.filter((t) => t.id !== confirmDeleteId),
              total_count: Math.max(0, prev.total_count - 1),
            }
          : prev
      );
      toast.success("Обращение удалено");
      setConfirmDeleteId(null);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      toast.error(msg || "Не удалось удалить");
    } finally {
      setDeleteLoading(false);
      setDeletingId(null);
    }
  };

  if (loading && !data && !accessDenied && !loadError) {
    return (
      <MainLayout>
        <Skeleton className="h-8 w-48 mb-6" />
        <Skeleton className="h-64 w-full" />
      </MainLayout>
    );
  }

  if (accessDenied) {
    return (
      <MainLayout>
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Доступ запрещён</AlertTitle>
          <AlertDescription>
            Только администраторы могут открывать эту страницу.
          </AlertDescription>
        </Alert>
      </MainLayout>
    );
  }

  const ticketRows = data?.tickets ?? [];
  const needsTableScroll = ticketRows.length > 15;

  return (
    <MainLayout>
      <AlertDialog
        open={confirmDeleteId != null}
        onOpenChange={(open) => {
          if (!open && !deleteLoading) setConfirmDeleteId(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Удалить обращение?</AlertDialogTitle>
            <AlertDialogDescription>
              Запись будет удалена без возможности восстановления.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteLoading}>Отмена</AlertDialogCancel>
            <AlertDialogAction
              disabled={deleteLoading}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={(e) => {
                e.preventDefault();
                void executeDelete();
              }}
            >
              {deleteLoading ? "Удаление…" : "Удалить"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <div className="flex items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-2">
          <Inbox className="h-7 w-7 text-primary" />
          <h1 className="text-2xl font-bold text-foreground">Обращения</h1>
          {data != null ? (
            <span className="text-sm text-muted-foreground">({data.total_count})</span>
          ) : null}
        </div>
        <Button variant="outline" asChild>
          <Link to="/admin" className="gap-2 inline-flex items-center">
            <Shield className="h-4 w-4" />
            Админ-панель
          </Link>
        </Button>
      </div>

      {loadError && (
        <Alert variant="destructive" className="mb-4">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Не удалось загрузить обращения</AlertTitle>
          <AlertDescription className="whitespace-pre-wrap break-words">{loadError}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader className="flex flex-row flex-wrap items-center gap-3 space-y-0 pb-4">
          <CardTitle className="text-base font-medium mb-0">Список обращений</CardTitle>
          <Select
            value={statusFilter}
            onValueChange={(v) => setStatusFilter(v as StatusFilter)}
            disabled={loading}
          >
            <SelectTrigger
              id="appeals-status-filter"
              className="w-[140px]"
              aria-label="Показать обращения: все, открытые или закрытые"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Все</SelectItem>
              <SelectItem value="open">Открыто</SelectItem>
              <SelectItem value="closed">Закрыто</SelectItem>
            </SelectContent>
          </Select>
        </CardHeader>
        <CardContent>
          {loading ? (
            <Skeleton className="h-40 w-full" />
          ) : loadError ? (
            <p className="text-sm text-muted-foreground">
              Проверьте подключение к API и обновите страницу.
            </p>
          ) : !data?.tickets?.length ? (
            <p className="text-sm text-muted-foreground">
              {statusFilter === "all" ? "Пока нет обращений." : "Нет обращений с выбранным статусом."}
            </p>
          ) : (
            <div
              className={cn(
                "max-w-full rounded-md border border-border",
                needsTableScroll &&
                  "max-h-[min(60vh,34rem)] overflow-auto overscroll-contain [scrollbar-gutter:stable] touch-pan-x touch-pan-y"
              )}
            >
              <Table
                wrapperClassName={needsTableScroll ? "overflow-visible" : undefined}
                className={cn(
                  "[&_td]:align-middle [&_th]:align-middle min-w-[1100px]",
                  "[&_thead_th]:sticky [&_thead_th]:top-0 [&_thead_th]:z-20",
                  "[&_thead_th]:border-b [&_thead_th]:border-border [&_thead_th]:bg-card/95 [&_thead_th]:backdrop-blur-sm"
                )}
              >
                <TableHeader>
                  <TableRow>
                    <TableHead
                      className="w-[100px] text-center"
                      title="Галочка — обращение закрыто"
                    >
                      Статус
                    </TableHead>
                    <TableHead className="whitespace-nowrap">Дата</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Имя</TableHead>
                    <TableHead>Тема</TableHead>
                    <TableHead className="whitespace-nowrap">Приоритет</TableHead>
                    <TableHead className="whitespace-nowrap">Категория</TableHead>
                    <TableHead className="min-w-[240px]">Описание</TableHead>
                    <TableHead className="w-[52px] text-center p-2">
                      <span className="sr-only">Удалить</span>
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.tickets.map((row) => {
                    const rowBusy = busyTicketId === row.id || deletingId === row.id;
                    return (
                      <TableRow key={row.id}>
                        <TableCell className="align-middle text-center">
                          <Checkbox
                            checked={Boolean(row.resolved)}
                            disabled={rowBusy}
                            onCheckedChange={(v) => void setTicketResolved(row.id, v === true)}
                            aria-label={
                              row.resolved ? "Снять «закрыто» (открыть обращение)" : "Отметить как закрыто"
                            }
                          />
                        </TableCell>
                        <TableCell className="whitespace-nowrap text-muted-foreground">
                          {formatRuDate(row.created_at)}
                        </TableCell>
                        <TableCell className="break-all max-w-[200px]">{row.email ?? "—"}</TableCell>
                        <TableCell className="max-w-[160px]">{row.full_name ?? "—"}</TableCell>
                        <TableCell className="font-medium max-w-[220px]">{row.subject}</TableCell>
                        <TableCell className="whitespace-nowrap">
                          {PRIORITY_RU[row.priority] ?? row.priority}
                        </TableCell>
                        <TableCell className="whitespace-nowrap">
                          {CATEGORY_RU[row.category] ?? row.category}
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground max-w-xl whitespace-pre-wrap break-words">
                          {row.description}
                        </TableCell>
                        <TableCell className="text-center p-1">
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-muted-foreground hover:text-destructive"
                            disabled={rowBusy}
                            aria-label="Удалить обращение"
                            onClick={() => setConfirmDeleteId(row.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </MainLayout>
  );
}
