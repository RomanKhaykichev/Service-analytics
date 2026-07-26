import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AlertCircle, ClipboardList, Shield, Trash2 } from "lucide-react";
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { apiDelete, apiGet, apiPatch } from "@/lib/api";
import { toast } from "sonner";
import { buildSurveyViewSections } from "@/lib/feedbackSurveyLabels";

interface FeedbackSurveyRow {
  id: string;
  user_id: string;
  email?: string | null;
  full_name?: string | null;
  answers: Record<string, unknown>;
  nps?: number | null;
  helpfulness?: number | null;
  client_name?: string | null;
  client_contact?: string | null;
  created_at: string;
  resolved: boolean;
}

interface FeedbackSurveysResponse {
  surveys: FeedbackSurveyRow[];
  total_count: number;
}

type StatusFilter = "all" | "open" | "closed";

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

function SurveyAnswersView({ answers }: { answers: Record<string, unknown> }) {
  const sections = useMemo(() => buildSurveyViewSections(answers || {}), [answers]);
  return (
    <div className="space-y-4">
      {sections.map((section) => (
        <Card key={section.title}>
          <CardHeader className="py-3">
            <CardTitle className="text-sm font-semibold">{section.title}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 pt-0">
            {section.rows.map((row) => (
              <div key={row.question} className="grid gap-1 sm:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)] sm:gap-3">
                <div className="text-sm text-muted-foreground">{row.question}</div>
                <div className="text-sm font-medium whitespace-pre-wrap break-words">{row.answer}</div>
              </div>
            ))}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export default function AdminFeedback() {
  const [accessDenied, setAccessDenied] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<FeedbackSurveysResponse | null>(null);
  const [viewRow, setViewRow] = useState<FeedbackSurveyRow | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [busySurveyId, setBusySurveyId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");

  const setSurveyResolved = useCallback(
    async (id: string, resolved: boolean) => {
      setBusySurveyId(id);
      try {
        await apiPatch<FeedbackSurveyRow>(`/api/admin/feedback-surveys/${id}`, { resolved });
        setData((prev) => {
          if (!prev) return prev;
          if (statusFilter === "open" && resolved) {
            return {
              ...prev,
              surveys: prev.surveys.filter((s) => s.id !== id),
              total_count: Math.max(0, prev.total_count - 1),
            };
          }
          if (statusFilter === "closed" && !resolved) {
            return {
              ...prev,
              surveys: prev.surveys.filter((s) => s.id !== id),
              total_count: Math.max(0, prev.total_count - 1),
            };
          }
          return {
            ...prev,
            surveys: prev.surveys.map((s) => (s.id === id ? { ...s, resolved } : s)),
          };
        });
        setViewRow((prev) => (prev?.id === id ? { ...prev, resolved } : prev));
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        toast.error(msg || "Не удалось сохранить");
      } finally {
        setBusySurveyId(null);
      }
    },
    [statusFilter]
  );

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    setAccessDenied(false);
    try {
      const res = await apiGet<FeedbackSurveysResponse>("/api/admin/feedback-surveys", {
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
    try {
      await apiDelete<{ ok: boolean }>(`/api/admin/feedback-surveys/${confirmDeleteId}`);
      setData((prev) =>
        prev
          ? {
              ...prev,
              surveys: prev.surveys.filter((s) => s.id !== confirmDeleteId),
              total_count: Math.max(0, prev.total_count - 1),
            }
          : prev
      );
      toast.success("Ответ удалён");
      setConfirmDeleteId(null);
      if (viewRow?.id === confirmDeleteId) setViewRow(null);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      toast.error(msg || "Не удалось удалить");
    } finally {
      setDeleteLoading(false);
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
          <AlertDescription>Только администраторы могут открывать эту страницу.</AlertDescription>
        </Alert>
      </MainLayout>
    );
  }

  const rows = data?.surveys ?? [];

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
            <AlertDialogTitle>Удалить ответ опросника?</AlertDialogTitle>
            <AlertDialogDescription>Запись будет удалена без возможности восстановления.</AlertDialogDescription>
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

      <Dialog open={viewRow != null} onOpenChange={(open) => !open && setViewRow(null)}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Опросник с ответами</DialogTitle>
            <DialogDescription>
              {viewRow
                ? `${viewRow.full_name || viewRow.client_name || "Пользователь"}${
                    viewRow.email ? ` · ${viewRow.email}` : ""
                  } · ${formatRuDate(viewRow.created_at)}`
                : null}
            </DialogDescription>
          </DialogHeader>
          {viewRow ? <SurveyAnswersView answers={viewRow.answers || {}} /> : null}
        </DialogContent>
      </Dialog>

      <div className="flex items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-2">
          <ClipboardList className="h-7 w-7 text-primary" />
          <h1 className="text-2xl font-bold text-foreground">Опросы</h1>
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
          <AlertTitle>Не удалось загрузить опросы</AlertTitle>
          <AlertDescription className="whitespace-pre-wrap break-words">{loadError}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader className="flex flex-row flex-wrap items-center gap-3 space-y-0 pb-4">
          <CardTitle className="text-base font-medium mb-0">Ответы клиентов</CardTitle>
          <Select
            value={statusFilter}
            onValueChange={(v) => setStatusFilter(v as StatusFilter)}
            disabled={loading}
          >
            <SelectTrigger
              id="feedback-status-filter"
              className="w-[140px]"
              aria-label="Показать опросы: все, открытые или закрытые"
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
          ) : rows.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              {statusFilter === "all" ? "Пока нет ответов на опросник." : "Нет опросов с выбранным статусом."}
            </p>
          ) : (
            <div className="overflow-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead
                      className="w-[100px] text-center"
                      title="Галочка — опрос закрыт"
                    >
                      Статус
                    </TableHead>
                    <TableHead>Дата</TableHead>
                    <TableHead>Пользователь</TableHead>
                    <TableHead>NPS</TableHead>
                    <TableHead>Польза</TableHead>
                    <TableHead>Контакт</TableHead>
                    <TableHead className="w-[140px]" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((row) => {
                    const rowBusy = busySurveyId === row.id || (deleteLoading && confirmDeleteId === row.id);
                    return (
                      <TableRow key={row.id}>
                        <TableCell className="align-middle text-center">
                          <Checkbox
                            checked={Boolean(row.resolved)}
                            disabled={rowBusy}
                            onCheckedChange={(v) => void setSurveyResolved(row.id, v === true)}
                            aria-label={
                              row.resolved ? "Снять «закрыто» (открыть опрос)" : "Отметить как закрыто"
                            }
                          />
                        </TableCell>
                        <TableCell className="whitespace-nowrap">{formatRuDate(row.created_at)}</TableCell>
                        <TableCell>
                          <div className="min-w-0">
                            <div className="font-medium truncate">
                              {row.full_name || row.client_name || "—"}
                            </div>
                            <div className="text-xs text-muted-foreground truncate">
                              {row.email || row.user_id}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell className="tabular-nums">{row.nps ?? "—"}</TableCell>
                        <TableCell className="tabular-nums">{row.helpfulness ?? "—"}</TableCell>
                        <TableCell className="max-w-[180px] truncate">
                          {row.client_contact || "—"}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1 justify-end">
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              onClick={() => setViewRow(row)}
                            >
                              Ответы
                            </Button>
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              className="text-destructive"
                              disabled={rowBusy}
                              onClick={() => setConfirmDeleteId(row.id)}
                              title="Удалить"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
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
