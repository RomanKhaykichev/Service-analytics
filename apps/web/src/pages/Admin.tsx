import { useState, useEffect, useCallback, useMemo } from "react";
import { Shield, Users, UserPlus, AlertCircle, Pencil, Trash2, UserMinus, CalendarPlus, Upload, BarChart3, ChevronUp, ChevronDown } from "lucide-react";
import { Tooltip as UITooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { MainLayout } from "@/components/layout/MainLayout";
import { useLanguage } from "@/contexts/LanguageContext";
import { useAuth } from "@/hooks/useAuth";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
  DialogFooter,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { useNavigate } from "react-router-dom";
import { apiGet, apiPatch, apiPost, apiDelete } from "@/lib/api";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

interface TenantRow {
  tenant_id: string;
  company_name?: string | null;
  owner_email?: string | null;
  phone?: string | null;
  created_at?: string | null;
  plan: string;
  trial_ends_at?: string | null;
  last_import_at?: string | null;
  last_import_status?: string | null;
  data_freshness_days?: number | null;
  imports_30d: number;
  failed_imports_30d: number;
  notes?: string | null;
  is_active: boolean;
  shops_count?: number;
  status?: string;
  trial_days_left?: number | null;
  paid?: boolean;
  paid_amount?: number | null; // Оплачено — сумма, которую оплатил клиент
  last_login_at?: string | null;
}

interface TenantsResponse {
  tenants: TenantRow[];
  total_count: number;
}

interface DashboardFunnel {
  visited_site: number;
  tried: number;
  registered: number;
  paid: number;
  conversion_pct: number;
}

interface DashboardFiles {
  total: number;
  errors: number;
  error_pct: number;
}

interface DashboardTotals {
  registered: number;
  paid_subscription: number;
  inactive_30d: number;
}

interface MonthlyRow {
  month: string;
  month_label: string;
  profit: number;
  registrations: number;
  payments: number;
  active_users: number;
}

interface DashboardMetrics {
  funnel: DashboardFunnel;
  files: DashboardFiles;
  totals: DashboardTotals;
  monthly: MonthlyRow[];
}

export default function Admin() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [tenants, setTenants] = useState<TenantsResponse | null>(null);
  const [loadingTenants, setLoadingTenants] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [accessDenied, setAccessDenied] = useState(false);
  const [search, setSearch] = useState("");
  const [planFilter, setPlanFilter] = useState<string>("all");
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [sort, setSort] = useState("created_at");
  type TenantSortColumn = "created_at" | "phone" | "shops_count" | "plan" | "trial_days_left" | "paid_amount" | "last_login_at" | "imports_30d" | null;
  const [sortColumn, setSortColumn] = useState<TenantSortColumn>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc" | null>(null);
  const [tenantShops, setTenantShops] = useState<Record<string, { loading: boolean; error: string | null; names: string[] }>>({});
  const [notesModal, setNotesModal] = useState<{ tenantId: string; notes: string } | null>(null);
  const [passwordModal, setPasswordModal] = useState<{ tenantId: string; newPassword: string } | null>(null);
  const [extendTrialModal, setExtendTrialModal] = useState<{ tenantId: string; days: number } | null>(null);
  const [confirmAction, setConfirmAction] = useState<null | { type: "disable" | "delete"; tenantId: string }>(null);
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [dashboardMetrics, setDashboardMetrics] = useState<DashboardMetrics | null>(null);
  const [loadingMetrics, setLoadingMetrics] = useState(true);
  const [funnelMonth, setFunnelMonth] = useState<string>("all");

  const fetchDashboardMetrics = useCallback(async (month?: string) => {
    setLoadingMetrics(true);
    try {
      const params = month && month !== "all" ? { funnel_month: month } : {};
      const data = await apiGet<DashboardMetrics>("/api/admin/dashboard-metrics", params);
      setDashboardMetrics(data);
    } catch {
      setDashboardMetrics(null);
    } finally {
      setLoadingMetrics(false);
    }
  }, []);

  const funnelMonthOptions = (() => {
    const options: { value: string; label: string }[] = [{ value: "all", label: "Общее" }];
    const now = new Date();
    const monthLabels = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"];
    for (let i = 0; i < 12; i++) {
      const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
      const y = d.getFullYear();
      const m = d.getMonth() + 1;
      const value = `${y}-${String(m).padStart(2, "0")}`;
      options.push({ value, label: `${monthLabels[m - 1]} ${y}` });
    }
    return options;
  })();

  const fetchTenants = useCallback(async () => {
    setLoadingTenants(true);
    setError(null);
    setAccessDenied(false);
      try {
        const params: Record<string, string | number> = {
          page,
          page_size: pageSize,
          sort,
        };
        if (search.trim()) params.search = search.trim();
        if (planFilter !== "all") {
          let planParam: string | null = null;
          if (planFilter === "trial") {
            planParam = "trial";
          } else if (planFilter === "month_5" || planFilter === "month_10") {
            planParam = "paid";
          }
          if (planParam) {
            params.plan = planParam;
          }
        }
      const data = await apiGet<TenantsResponse>("/api/admin/tenants", params);
      setTenants(data);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      if (msg.includes("403") || msg.includes("Admin")) {
        setAccessDenied(true);
      } else {
        setError(msg);
      }
    } finally {
      setLoadingTenants(false);
    }
  }, [page, pageSize, sort, search, planFilter]);

  const loadTenantShops = useCallback(async (tenantId: string) => {
    setTenantShops((prev) => {
      const current = prev[tenantId];
      if (current?.loading || current?.names?.length) return prev;
      return { ...prev, [tenantId]: { loading: true, error: null, names: current?.names ?? [] } };
    });
    try {
      const res = await apiGet<{ tenant_id: string; shops: string[] }>(`/api/admin/tenants/${tenantId}/shops`);
      setTenantShops((prev) => ({
        ...prev,
        [tenantId]: { loading: false, error: null, names: res.shops ?? [] },
      }));
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setTenantShops((prev) => ({
        ...prev,
        [tenantId]: { loading: false, error: msg, names: prev[tenantId]?.names ?? [] },
      }));
    }
  }, []);

  const handleTenantSort = (column: TenantSortColumn) => {
    if (!column) return;
    if (sortColumn === column) {
      if (sortDirection === "asc") setSortDirection("desc");
      else if (sortDirection === "desc") {
        setSortDirection(null);
        setSortColumn(null);
      } else {
        setSortDirection("asc");
      }
    } else {
      setSortColumn(column);
      setSortDirection("asc");
    }
  };

  const getPlanSortKey = (row: TenantRow) => {
    const rawPlan = (row.plan || "").trim().toLowerCase();
    if (!rawPlan || rawPlan === "trial") return 0;       // Trial 10
    if (rawPlan === "month_5" || rawPlan === "month 5" || rawPlan === "month5") return 1; // Month 5
    if (rawPlan === "month_10" || rawPlan === "month 10" || rawPlan === "month10") return 2; // Month 10
    if (rawPlan === "gold" || rawPlan === "gold_plan") return 3; // Gold
    return 4; // прочие / неизвестные
  };

  const sortedTenants = useMemo(() => {
    const list = tenants?.tenants ?? [];
    if (!sortColumn || !sortDirection) return list;
    return [...list].sort((a, b) => {
      let aVal: string | number | null | undefined;
      let bVal: string | number | null | undefined;
      switch (sortColumn) {
        case "created_at":
          aVal = a.created_at ?? "";
          bVal = b.created_at ?? "";
          return sortDirection === "asc" ? String(aVal).localeCompare(String(bVal)) : String(bVal).localeCompare(String(aVal));
        case "phone":
          aVal = a.phone ?? "";
          bVal = b.phone ?? "";
          return sortDirection === "asc" ? String(aVal).localeCompare(String(bVal)) : String(bVal).localeCompare(String(aVal));
        case "shops_count":
          aVal = a.shops_count ?? -1;
          bVal = b.shops_count ?? -1;
          return sortDirection === "asc" ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number);
        case "plan":
          aVal = getPlanSortKey(a);
          bVal = getPlanSortKey(b);
          return sortDirection === "asc" ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number);
        case "trial_days_left":
          aVal = a.trial_days_left ?? -1;
          bVal = b.trial_days_left ?? -1;
          return sortDirection === "asc" ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number);
        case "paid_amount":
          aVal = a.paid_amount ?? 0;
          bVal = b.paid_amount ?? 0;
          return sortDirection === "asc" ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number);
        case "last_login_at":
          aVal = a.last_login_at ?? "";
          bVal = b.last_login_at ?? "";
          return sortDirection === "asc" ? String(aVal).localeCompare(String(bVal)) : String(bVal).localeCompare(String(aVal));
        case "imports_30d":
          aVal = a.imports_30d ?? 0;
          bVal = b.imports_30d ?? 0;
          return sortDirection === "asc" ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number);
        default:
          return 0;
      }
    });
  }, [tenants?.tenants, sortColumn, sortDirection]);

  useEffect(() => {
    if (!accessDenied) {
      fetchTenants();
      fetchDashboardMetrics();
    }
  }, [accessDenied, fetchTenants, fetchDashboardMetrics]);

  const handleDisable = async (tenantId: string) => {
    setConfirmAction({ type: "disable", tenantId });
  };

  const handleEnable = async (tenantId: string) => {
    try {
      await apiPost(`/api/admin/tenants/${tenantId}/enable`, {});
      fetchTenants();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const handleExtendTrial = async (tenantId: string, days: number) => {
    try {
      await apiPost(`/api/admin/tenants/${tenantId}/extend-trial`, { days });
      setExtendTrialModal(null);
      fetchTenants();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const handleSaveNotes = async () => {
    if (!notesModal) return;
    try {
      await apiPatch(`/api/admin/tenants/${notesModal.tenantId}/notes`, { notes: notesModal.notes });
      setNotesModal(null);
      fetchTenants();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const handleSetPassword = async () => {
    if (!passwordModal || !passwordModal.newPassword.trim() || passwordModal.newPassword.length < 6) {
      toast.error("Пароль не менее 6 символов");
      return;
    }
    try {
      await apiPost(`/api/admin/tenants/${passwordModal.tenantId}/set-password`, {
        password: passwordModal.newPassword,
      });
      setPasswordModal(null);
      setError(null);
      toast.success("Пароль успешно обновлён");
      fetchTenants();
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      toast.error(msg || "Ошибка при сохранении пароля");
      setError(msg);
    }
  };

  const handleDeleteTenant = async (tenantId: string) => {
    setConfirmAction({ type: "delete", tenantId });
  };

  if (accessDenied) {
    return (
      <MainLayout>
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Доступ запрещён</AlertTitle>
          <AlertDescription>
            Только администраторы могут открывать эту страницу. Укажите ADMIN_USER_IDS в .env API.
          </AlertDescription>
        </Alert>
      </MainLayout>
    );
  }

  const runConfirmAction = async () => {
    if (!confirmAction) return;
    setConfirmLoading(true);
    try {
      if (confirmAction.type === "disable") {
        await apiPost(`/api/admin/tenants/${confirmAction.tenantId}/disable`, {});
        toast.success("Тенант отключён");
      } else {
        await apiDelete(`/api/admin/tenants/${confirmAction.tenantId}`);
        toast.success("Тенант удалён");
      }
      setConfirmAction(null);
      fetchTenants();
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      toast.error(msg || "Ошибка");
    } finally {
      setConfirmLoading(false);
    }
  };

  const handleExitToService = () => {
    navigate("/");
  };

  return (
    <MainLayout>
      <div className="flex items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-2">
          <Shield className="h-7 w-7" />
          <h1 className="text-2xl font-bold text-foreground">{t("header.adminPanel")}</h1>
        </div>
        <Button
          onClick={handleExitToService}
          className="bg-primary text-primary-foreground hover:bg-primary/90 rounded-lg shadow-md hover:shadow-lg transition-shadow shrink-0"
        >
          Выйти
        </Button>
      </div>

      <AlertDialog
        open={confirmAction != null}
        onOpenChange={(open) => {
          if (!open && !confirmLoading) setConfirmAction(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {confirmAction?.type === "delete" ? "Удалить тенанта?" : "Отключить тенанта?"}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {confirmAction?.type === "delete"
                ? "Действие необратимо: аккаунт и все загруженные данные будут удалены."
                : "Пользователь не сможет входить в систему, пока вы не включите аккаунт обратно."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={confirmLoading}>Отмена</AlertDialogCancel>
            <AlertDialogAction
              disabled={confirmLoading}
              className={confirmAction?.type === "delete" ? "bg-destructive text-destructive-foreground hover:bg-destructive/90" : undefined}
              onClick={(e) => {
                e.preventDefault();
                runConfirmAction();
              }}
            >
              {confirmLoading ? "Подождите…" : confirmAction?.type === "delete" ? "Удалить" : "Отключить"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Ошибка</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Метрики: воронка | всего + файлы | таблица по месяцам */}
      {!accessDenied && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] gap-4 mb-6 items-stretch">
            {/* Колонка 1: Воронка пользователей */}
            <Card className="flex flex-col min-h-[280px]">
              <CardHeader className="pb-2 flex flex-row items-center justify-between gap-2 shrink-0">
                <CardTitle className="text-sm font-medium uppercase tracking-wide text-muted-foreground">
                  Воронка пользователей
                </CardTitle>
                <Select
                  value={funnelMonth}
                  onValueChange={(v) => {
                    setFunnelMonth(v);
                    fetchDashboardMetrics(v);
                  }}
                >
                  <SelectTrigger className="w-[140px] h-8 text-xs">
                    <SelectValue placeholder="Общее" />
                  </SelectTrigger>
                  <SelectContent>
                    {funnelMonthOptions.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </CardHeader>
              <CardContent className="space-y-1 flex-1">
                {loadingMetrics ? (
                  <Skeleton className="h-24 w-full" />
                ) : dashboardMetrics ? (
                  (() => {
                    const maxVal = Math.max(
                      dashboardMetrics.funnel.visited_site,
                      dashboardMetrics.funnel.tried,
                      dashboardMetrics.funnel.registered,
                      dashboardMetrics.funnel.paid,
                      1
                    );
                    const rows = [
                      { n: dashboardMetrics.funnel.visited_site, label: "Зашли на сайт", pct: null as number | null },
                      { n: dashboardMetrics.funnel.tried, label: "Попробовали", pct: dashboardMetrics.funnel.visited_site ? Math.round((dashboardMetrics.funnel.tried / dashboardMetrics.funnel.visited_site) * 100) : 0 },
                      { n: dashboardMetrics.funnel.registered, label: "Зарегистрировались", pct: dashboardMetrics.funnel.tried ? Math.round((dashboardMetrics.funnel.registered / dashboardMetrics.funnel.tried) * 100) : 0 },
                      { n: dashboardMetrics.funnel.paid, label: "Оплатили", pct: dashboardMetrics.funnel.registered ? Math.round((dashboardMetrics.funnel.paid / dashboardMetrics.funnel.registered) * 100) : 0 },
                    ];
                    return (
                      <>
                        {rows.map(({ n, label, pct }, i) => (
                          <div key={i} className="flex items-center gap-2">
                            <span className="font-bold w-8 shrink-0">{n}</span>
                            <div className="flex-1 min-w-0 flex justify-center">
                              <div
                                className="h-8 flex items-center justify-center text-white text-sm font-medium rounded min-w-[60px]"
                                style={{
                                  background: "hsl(var(--primary))",
                                  width: `${Math.max((n / maxVal) * 100, n > 0 ? 8 : 0)}%`,
                                }}
                              >
                                {label}
                              </div>
                            </div>
                            <span className="text-sm font-medium text-muted-foreground shrink-0 w-10 text-right">{pct != null ? `${pct}%` : ""}</span>
                          </div>
                        ))}
                        <p className="text-sm font-bold text-primary pt-2">
                          Конверсия: {dashboardMetrics.funnel.conversion_pct}%
                        </p>
                      </>
                    );
                  })()
                ) : null}
              </CardContent>
            </Card>

            {/* Колонка 2: Всего зарегистрировано (сверху) + Загружено файлов (снизу), ширина по заголовку */}
            <div className="flex flex-col gap-2 min-h-[280px] w-max max-w-full">
              <Card className="flex-1 min-h-0 flex flex-col">
                <CardHeader className="pb-2 shrink-0">
          <CardTitle className="text-sm font-medium uppercase tracking-wide text-muted-foreground flex items-center gap-2">
            <Users className="h-4 w-4 text-primary" />
            Всего зарегистрировано
          </CardTitle>
                </CardHeader>
                <CardContent className="flex-1">
                  {loadingMetrics ? (
                    <Skeleton className="h-16 w-full" />
                  ) : dashboardMetrics ? (
                    <>
                      <p className="text-2xl font-bold">{dashboardMetrics.totals.registered}</p>
                      <p className="text-sm text-muted-foreground">Платная подписка: {dashboardMetrics.totals.paid_subscription}</p>
                      <p className="text-sm text-muted-foreground">Неактивны более 30 дней: {dashboardMetrics.totals.inactive_30d}</p>
                    </>
                  ) : null}
                </CardContent>
              </Card>
              <Card className="flex-1 min-h-0 flex flex-col">
                <CardHeader className="pb-2 shrink-0">
                  <CardTitle className="text-sm font-medium uppercase tracking-wide text-muted-foreground flex items-center gap-2">
                    <Upload className="h-4 w-4 text-primary" />
                    Загружено файлов
                  </CardTitle>
                </CardHeader>
                <CardContent className="flex-1">
                  {loadingMetrics ? (
                    <Skeleton className="h-16 w-full" />
                  ) : dashboardMetrics ? (
                    <>
                      <p className="text-2xl font-bold">{dashboardMetrics.files.total}</p>
                      <p className="text-sm text-muted-foreground">Из них ошибок: {dashboardMetrics.files.errors}</p>
                      <p className="text-sm text-muted-foreground">Процент ошибки: {dashboardMetrics.files.error_pct}%</p>
                    </>
                  ) : null}
                </CardContent>
              </Card>
            </div>

            {/* Колонка 3: Таблица по месяцам (прибыль), та же ширина, прокрутка при избытке данных */}
            <Card className="flex flex-col min-h-[280px] min-w-0">
              <CardHeader className="pb-2 shrink-0">
                <CardTitle className="text-sm font-medium uppercase tracking-wide text-muted-foreground">
                  Прибыль по месяцам
                </CardTitle>
              </CardHeader>
              <CardContent className="flex-1 min-h-0 overflow-auto p-0">
                {dashboardMetrics && dashboardMetrics.monthly.length > 0 ? (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="px-3">Месяц</TableHead>
                        <TableHead className="text-center px-3">Прибыль</TableHead>
                        <TableHead
                          className="text-center px-3"
                          title={t("admin.monthly.registrationsHelp")}
                        >
                          Регистрации
                        </TableHead>
                        <TableHead className="text-center px-3">Оплат</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {dashboardMetrics.monthly.map((row) => (
                        <TableRow key={row.month}>
                          <TableCell className="px-3">{row.month_label}</TableCell>
                          <TableCell className="text-center px-3">
                            {row.profit > 0 ? `${Number(row.profit).toLocaleString("ru-RU", { maximumFractionDigits: 0 })} сум` : "0"}
                          </TableCell>
                          <TableCell className="text-center px-3">{row.registrations}</TableCell>
                          <TableCell className="text-center px-3">{row.payments}</TableCell>
                        </TableRow>
                      ))}
                      <TableRow className="font-semibold bg-muted/50">
                        <TableCell className="px-3">Всего</TableCell>
                        <TableCell className="text-center px-3">
                          {dashboardMetrics.monthly.reduce((s, r) => s + r.profit, 0).toLocaleString("ru-RU", { maximumFractionDigits: 0 })} сум
                        </TableCell>
                        <TableCell className="text-center px-3">
                          {dashboardMetrics.monthly.reduce((s, r) => s + r.registrations, 0)}
                        </TableCell>
                        <TableCell className="text-center px-3">
                          {dashboardMetrics.monthly.reduce((s, r) => s + r.payments, 0)}
                        </TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                ) : (
                  <div className="p-4 text-sm text-muted-foreground">
                    Нет данных
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* График Аналитика подписок: доход (столбцы) + подписчики (линия) */}
          {dashboardMetrics && dashboardMetrics.monthly.length > 0 && (
            <Card className="mb-6">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base">
                  <BarChart3 className="h-5 w-5 text-primary" />
                  {t("admin.subscriptions.title")}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={320}>
                  <ComposedChart
                    data={dashboardMetrics.monthly}
                    margin={{ top: 8, right: 8, left: 4, bottom: 4 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month_label" tick={{ fontSize: 10 }} />
                    <YAxis
                      yAxisId="left"
                      tick={{ fontSize: 10 }}
                      tickFormatter={(v) =>
                        v >= 1e6
                          ? `${(v / 1e6).toFixed(1)}M`
                          : v >= 1e3
                          ? `${(v / 1e3).toFixed(0)}k`
                          : String(v)
                      }
                      label={{
                        value: t("admin.subscriptions.revenue"),
                        angle: -90,
                        position: "insideLeft",
                        style: { fontSize: 11 },
                      }}
                    />
                    <YAxis
                      yAxisId="right"
                      orientation="right"
                      tick={{ fontSize: 10 }}
                      label={{
                        value: t("admin.subscriptions.subscribers"),
                        angle: 90,
                        position: "insideRight",
                        style: { fontSize: 11 },
                      }}
                    />
                    <Tooltip
                      formatter={(value: number, _name: string, entry: any) => {
                        if (entry?.dataKey === "profit") {
                          return [
                            Number(value).toLocaleString("ru-RU", {
                              maximumFractionDigits: 0,
                            }),
                            t("admin.subscriptions.revenue"),
                          ];
                        }
                        if (entry?.dataKey === "active_users") {
                          return [value, t("admin.subscriptions.subscribers")];
                        }
                        return [value, entry?.name];
                      }}
                      labelFormatter={(label) => label}
                    />
                    <Legend />
                    <Bar
                      yAxisId="left"
                      dataKey="profit"
                      fill="hsl(var(--primary))"
                      name={t("admin.subscriptions.revenue")}
                      barSize={24}
                      radius={[2, 2, 0, 0]}
                    />
                    <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="active_users"
                      stroke="hsl(var(--primary))"
                      strokeWidth={2}
                      name={t("admin.subscriptions.subscribers")}
                      dot={{ r: 4, fill: "hsl(var(--background))", stroke: "hsl(var(--primary))" }}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Таблица Пользователи */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5 text-primary" />
            Пользователи {tenants != null ? `(${tenants.total_count})` : ""}
          </CardTitle>
          <div className="flex flex-wrap gap-2 mt-2">
            <Input
              placeholder="Поиск (email, имя, ID)..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  setPage(1);
                  fetchTenants();
                }
              }}
              className="max-w-xs"
            />
            <Select value={planFilter} onValueChange={setPlanFilter}>
              <SelectTrigger className="w-[120px]">
                <SelectValue placeholder="Plan" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Все</SelectItem>
                <SelectItem value="trial">Trial 10</SelectItem>
                <SelectItem value="month_5">Month 5</SelectItem>
                <SelectItem value="month_10">Month 10</SelectItem>
              </SelectContent>
            </Select>
            <Button onClick={() => { setPage(1); fetchTenants(); }}>Применить</Button>
          </div>
        </CardHeader>
        <CardContent>
          {loadingTenants ? (
            <Skeleton className="h-64 w-full" />
          ) : tenants ? (
            <>
              <div className="overflow-x-auto -mx-1">
                <Table className="min-w-[1700px] [&_th]:h-10 [&_th]:py-2 [&_th]:px-3 [&_td]:py-2 [&_td]:px-3">
                <TableHeader>
                  <TableRow>
                    <TableHead className="sticky left-0 z-10 bg-card border-r border-border min-w-[200px] max-w-[260px]">Аккаунт</TableHead>
                    <TableHead className="text-center">
                      <button
                        type="button"
                        onClick={() => handleTenantSort("created_at")}
                        className="inline-flex items-center justify-center gap-0.5 hover:text-foreground transition-colors w-full"
                      >
                        Регистрация
                        <span className="flex flex-col">
                          <ChevronUp className={cn("h-3 w-3 -mb-1", sortColumn === "created_at" && sortDirection === "asc" ? "text-primary" : "text-muted-foreground/50")} />
                          <ChevronDown className={cn("h-3 w-3", sortColumn === "created_at" && sortDirection === "desc" ? "text-primary" : "text-muted-foreground/50")} />
                        </span>
                      </button>
                    </TableHead>
                    <TableHead className="text-center">
                      <button type="button" onClick={() => handleTenantSort("phone")} className="inline-flex items-center justify-center gap-0.5 hover:text-foreground transition-colors w-full">
                        Телефон
                        <span className="flex flex-col">
                          <ChevronUp className={cn("h-3 w-3 -mb-1", sortColumn === "phone" && sortDirection === "asc" ? "text-primary" : "text-muted-foreground/50")} />
                          <ChevronDown className={cn("h-3 w-3", sortColumn === "phone" && sortDirection === "desc" ? "text-primary" : "text-muted-foreground/50")} />
                        </span>
                      </button>
                    </TableHead>
                    <TableHead className="text-center">
                      <button type="button" onClick={() => handleTenantSort("shops_count")} className="inline-flex items-center justify-center gap-0.5 hover:text-foreground transition-colors w-full">
                        Магазин
                        <span className="flex flex-col">
                          <ChevronUp className={cn("h-3 w-3 -mb-1", sortColumn === "shops_count" && sortDirection === "asc" ? "text-primary" : "text-muted-foreground/50")} />
                          <ChevronDown className={cn("h-3 w-3", sortColumn === "shops_count" && sortDirection === "desc" ? "text-primary" : "text-muted-foreground/50")} />
                        </span>
                      </button>
                    </TableHead>
                    <TableHead className="text-center">
                      <button type="button" onClick={() => handleTenantSort("plan")} className="inline-flex items-center justify-center gap-0.5 hover:text-foreground transition-colors w-full">
                        Тариф
                        <span className="flex flex-col">
                          <ChevronUp className={cn("h-3 w-3 -mb-1", sortColumn === "plan" && sortDirection === "asc" ? "text-primary" : "text-muted-foreground/50")} />
                          <ChevronDown className={cn("h-3 w-3", sortColumn === "plan" && sortDirection === "desc" ? "text-primary" : "text-muted-foreground/50")} />
                        </span>
                      </button>
                    </TableHead>
                    <TableHead className="text-center">
                      <button type="button" onClick={() => handleTenantSort("trial_days_left")} className="inline-flex items-center justify-center gap-0.5 hover:text-foreground transition-colors w-full">
                        Статус подписки
                        <span className="flex flex-col">
                          <ChevronUp className={cn("h-3 w-3 -mb-1", sortColumn === "trial_days_left" && sortDirection === "asc" ? "text-primary" : "text-muted-foreground/50")} />
                          <ChevronDown className={cn("h-3 w-3", sortColumn === "trial_days_left" && sortDirection === "desc" ? "text-primary" : "text-muted-foreground/50")} />
                        </span>
                      </button>
                    </TableHead>
                    <TableHead className="text-center">
                      <button type="button" onClick={() => handleTenantSort("trial_days_left")} className="inline-flex items-center justify-center gap-0.5 hover:text-foreground transition-colors w-full">
                        Остаток дней
                        <span className="flex flex-col">
                          <ChevronUp className={cn("h-3 w-3 -mb-1", sortColumn === "trial_days_left" && sortDirection === "asc" ? "text-primary" : "text-muted-foreground/50")} />
                          <ChevronDown className={cn("h-3 w-3", sortColumn === "trial_days_left" && sortDirection === "desc" ? "text-primary" : "text-muted-foreground/50")} />
                        </span>
                      </button>
                    </TableHead>
                    <TableHead className="text-center">
                      <button type="button" onClick={() => handleTenantSort("paid_amount")} className="inline-flex items-center justify-center gap-0.5 hover:text-foreground transition-colors w-full">
                        Оплачено
                        <span className="flex flex-col">
                          <ChevronUp className={cn("h-3 w-3 -mb-1", sortColumn === "paid_amount" && sortDirection === "asc" ? "text-primary" : "text-muted-foreground/50")} />
                          <ChevronDown className={cn("h-3 w-3", sortColumn === "paid_amount" && sortDirection === "desc" ? "text-primary" : "text-muted-foreground/50")} />
                        </span>
                      </button>
                    </TableHead>
                    <TableHead className="text-center">
                      <button type="button" onClick={() => handleTenantSort("last_login_at")} className="inline-flex items-center justify-center gap-0.5 hover:text-foreground transition-colors w-full">
                        Дата входа
                        <span className="flex flex-col">
                          <ChevronUp className={cn("h-3 w-3 -mb-1", sortColumn === "last_login_at" && sortDirection === "asc" ? "text-primary" : "text-muted-foreground/50")} />
                          <ChevronDown className={cn("h-3 w-3", sortColumn === "last_login_at" && sortDirection === "desc" ? "text-primary" : "text-muted-foreground/50")} />
                        </span>
                      </button>
                    </TableHead>
                    <TableHead className="text-center">
                      <button type="button" onClick={() => handleTenantSort("imports_30d")} className="inline-flex items-center justify-center gap-0.5 hover:text-foreground transition-colors w-full">
                        Импорты 30д
                        <span className="flex flex-col">
                          <ChevronUp className={cn("h-3 w-3 -mb-1", sortColumn === "imports_30d" && sortDirection === "asc" ? "text-primary" : "text-muted-foreground/50")} />
                          <ChevronDown className={cn("h-3 w-3", sortColumn === "imports_30d" && sortDirection === "desc" ? "text-primary" : "text-muted-foreground/50")} />
                        </span>
                      </button>
                    </TableHead>
                    <TableHead className="text-center whitespace-nowrap">Notes</TableHead>
                    <TableHead className="text-center whitespace-nowrap">Действия</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody className="[&_tr]:bg-card">
                  {sortedTenants.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={12} className="text-center text-muted-foreground">
                        Нет тенантов
                      </TableCell>
                    </TableRow>
                  ) : (
                    sortedTenants.map((row) => (
                      <TableRow key={row.tenant_id}>
                        <TableCell className="sticky left-0 z-10 bg-card border-r border-border min-w-[200px] max-w-[260px]">
                          <div className="font-medium">{row.company_name || row.owner_email || row.tenant_id.slice(0, 8)}</div>
                          {row.owner_email && (
                            <div className="text-xs text-muted-foreground">{row.owner_email}</div>
                          )}
                        </TableCell>
                        <TableCell className="text-center">{row.created_at ?? "—"}</TableCell>
                        <TableCell className="text-center">{row.phone ?? "—"}</TableCell>
                        <TableCell className="text-center">
                          {row.shops_count != null && row.shops_count > 0 ? (
                            <UITooltip>
                              <TooltipTrigger asChild>
                                <button
                                  type="button"
                                  className="underline-offset-2 hover:underline font-medium"
                                  onMouseEnter={() => loadTenantShops(row.tenant_id)}
                                >
                                  {row.shops_count}
                                </button>
                              </TooltipTrigger>
                              <TooltipContent className="max-w-xs whitespace-pre-line">
                                {tenantShops[row.tenant_id]?.loading && "Загрузка магазинов…"}
                                {tenantShops[row.tenant_id]?.error &&
                                  !tenantShops[row.tenant_id]?.loading &&
                                  `Ошибка: ${tenantShops[row.tenant_id]?.error}`}
                                {!tenantShops[row.tenant_id]?.loading &&
                                  !tenantShops[row.tenant_id]?.error &&
                                  (tenantShops[row.tenant_id]?.names?.length
                                    ? tenantShops[row.tenant_id].names.join("\n")
                                    : "Магазины не найдены")}
                              </TooltipContent>
                            </UITooltip>
                          ) : (
                            "—"
                          )}
                        </TableCell>
                        <TableCell className="text-center">
                          {(() => {
                            const rawPlan = (row.plan || "").trim().toLowerCase();
                            let label: string;

                            // План из БД
                            if (!rawPlan || rawPlan === "trial") {
                              label = "Trial 10";
                            } else if (rawPlan === "month_5" || rawPlan === "month 5" || rawPlan === "month5") {
                              label = "Month 5";
                            } else if (rawPlan === "month_10" || rawPlan === "month 10" || rawPlan === "month10") {
                              label = "Month 10";
                            } else if (rawPlan === "gold" || rawPlan === "gold_plan") {
                              label = "Gold";
                            } else {
                              // Неподдержанные значения показываем как есть
                              label = row.plan || "—";
                            }

                            const pillClass =
                              label === "Trial 10"
                                ? "bg-gradient-to-br from-sky-100 via-slate-100 to-amber-50 text-gray-800 shadow-sm shadow-gray-400/25"
                                : label === "Gold"
                                  ? "bg-gradient-to-br from-amber-200 via-yellow-100 to-amber-400 text-amber-900 shadow-md shadow-amber-500/40"
                                  : label === "Month 5"
                                    ? "bg-gradient-to-r from-indigo-300 to-violet-100 text-indigo-900"
                                    : label === "Month 10"
                                      ? "bg-blue-400 text-white shadow-md shadow-blue-600/30"
                                      : "bg-muted text-muted-foreground";

                            return (
                              <span
                                className={`inline-block rounded-full px-3 py-1.5 text-sm font-medium ${pillClass}`}
                              >
                                {label}
                              </span>
                            );
                          })()}
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge
                            variant="secondary"
                            className={
                              row.trial_days_left != null && row.trial_days_left > 0
                                ? "bg-green-500 text-white"
                                : "bg-red-500 text-white"
                            }
                          >
                            {row.trial_days_left != null && row.trial_days_left > 0
                              ? t("profile.active")
                              : t("profile.inactive")}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-center font-medium">{row.trial_days_left != null ? row.trial_days_left : "—"}</TableCell>
                        <TableCell className="text-center">
                          {row.paid_amount != null && row.paid_amount !== 0
                            ? Number(row.paid_amount).toLocaleString("ru-RU", { minimumFractionDigits: 0, maximumFractionDigits: 2 })
                            : row.paid
                              ? "Да"
                              : "—"}
                        </TableCell>
                        <TableCell className="text-center">{row.last_login_at ? row.last_login_at.slice(0, 10) : "—"}</TableCell>
                        <TableCell className="text-center font-medium">{row.imports_30d}</TableCell>
                        <TableCell className="text-center">
                          {row.notes && row.notes.trim() ? (
                            <UITooltip>
                              <TooltipTrigger asChild>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  className="bg-zinc-300 text-zinc-800 hover:bg-zinc-400"
                                  onClick={() =>
                                    setNotesModal({
                                      tenantId: row.tenant_id,
                                      notes: row.notes ?? "",
                                    })
                                  }
                                >
                                  Note
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent className="max-w-xs break-words">
                                {row.notes}
                              </TooltipContent>
                            </UITooltip>
                          ) : (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() =>
                                setNotesModal({
                                  tenantId: row.tenant_id,
                                  notes: row.notes ?? "",
                                })
                              }
                            >
                              Edit
                            </Button>
                          )}
                        </TableCell>
                        <TableCell className="text-center">
                          {row.owner_email && row.owner_email === user?.email ? (
                            "—"
                          ) : (
                            <div className="flex flex-wrap gap-1 justify-center items-center">
                              {row.is_active ? (
                                <UITooltip>
                                  <TooltipTrigger asChild>
                                    <Button
                                      size="icon"
                                      variant="ghost"
                                      className="h-8 w-8"
                                      onClick={() => handleDisable(row.tenant_id)}
                                    >
                                      <UserMinus className="h-4 w-4" />
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    {t("admin.tooltip.disableTenant")}
                                  </TooltipContent>
                                </UITooltip>
                              ) : (
                                <UITooltip>
                                  <TooltipTrigger asChild>
                                    <Button
                                      size="icon"
                                      variant="ghost"
                                      className="h-8 w-8"
                                      onClick={() => handleEnable(row.tenant_id)}
                                    >
                                      <UserPlus className="h-4 w-4" />
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    {t("admin.tooltip.enableTenant")}
                                  </TooltipContent>
                                </UITooltip>
                              )}
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Button
                                    size="icon"
                                    variant="ghost"
                                    className="h-8 w-8"
                                    onClick={() =>
                                      setExtendTrialModal({
                                        tenantId: row.tenant_id,
                                        days: 7,
                                      })
                                    }
                                  >
                                    <CalendarPlus className="h-4 w-4" />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>
                                  {t("admin.tooltip.extendTrial")}
                                </TooltipContent>
                              </UITooltip>
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Button
                                    size="icon"
                                    variant="ghost"
                                    className="h-8 w-8"
                                    onClick={() =>
                                      setPasswordModal({
                                        tenantId: row.tenant_id,
                                        newPassword: "",
                                      })
                                    }
                                  >
                                    <Pencil className="h-4 w-4" />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>
                                  {t("admin.tooltip.changePassword")}
                                </TooltipContent>
                              </UITooltip>
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Button
                                    size="icon"
                                    variant="ghost"
                                    className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
                                    onClick={() => handleDeleteTenant(row.tenant_id)}
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>
                                  {t("admin.tooltip.deleteTenant")}
                                </TooltipContent>
                              </UITooltip>
                            </div>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
              </div>
              <div className="flex items-center justify-end mt-4">
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => p - 1)}
                  >
                    Назад
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={page * pageSize >= tenants.total_count}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Вперёд
                  </Button>
                </div>
              </div>
            </>
          ) : null}
        </CardContent>
      </Card>

      <Dialog open={!!notesModal} onOpenChange={(open) => !open && setNotesModal(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Заметки по тенанту</DialogTitle>
          </DialogHeader>
          {notesModal && (
            <Textarea
              value={notesModal.notes}
              onChange={(e) => setNotesModal((p) => (p ? { ...p, notes: e.target.value } : null))}
              rows={4}
              placeholder="Внутренние заметки..."
            />
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setNotesModal(null)}>Отмена</Button>
            <Button onClick={handleSaveNotes}>Сохранить</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!passwordModal} onOpenChange={(open) => !open && setPasswordModal(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Сменить пароль / Сброс пароля</DialogTitle>
            <p className="text-sm text-muted-foreground">
              Пароль хранится в виде хеша, просмотр невозможен. Задайте новый пароль (не менее 6 символов).
            </p>
          </DialogHeader>
          {passwordModal && (
            <div className="space-y-2">
              <label className="text-sm font-medium">Новый пароль</label>
              <Input
                type="password"
                value={passwordModal.newPassword}
                onChange={(e) => setPasswordModal((p) => (p ? { ...p, newPassword: e.target.value } : null))}
                placeholder="Минимум 6 символов"
              />
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setPasswordModal(null)}>Отмена</Button>
            <Button onClick={handleSetPassword}>Сохранить пароль</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!extendTrialModal} onOpenChange={(open) => !open && setExtendTrialModal(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Добавить дни триала</DialogTitle>
            <p className="text-sm text-muted-foreground">Выберите количество дней или введите своё значение.</p>
          </DialogHeader>
          {extendTrialModal && (
            <div className="space-y-4">
              <div className="flex flex-wrap gap-2">
                {[7, 14, 30].map((d) => (
                  <Button
                    key={d}
                    variant={extendTrialModal.days === d ? "default" : "outline"}
                    onClick={() => setExtendTrialModal((p) => (p ? { ...p, days: d } : null))}
                  >
                    +{d} дней
                  </Button>
                ))}
              </div>
              <div className="flex items-center gap-2">
                <label className="text-sm font-medium whitespace-nowrap">Своё значение:</label>
                <Input
                  type="number"
                  min={1}
                  max={365}
                  value={extendTrialModal.days}
                  onChange={(e) => {
                    const v = parseInt(e.target.value, 10);
                    if (!Number.isNaN(v) && v >= 1 && v <= 365) {
                      setExtendTrialModal((p) => (p ? { ...p, days: v } : null));
                    }
                  }}
                  className="w-24"
                />
                <span className="text-sm text-muted-foreground">дней</span>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setExtendTrialModal(null)}>Отмена</Button>
            <Button onClick={() => extendTrialModal && handleExtendTrial(extendTrialModal.tenantId, extendTrialModal.days)}>
              Добавить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </MainLayout>
  );
}
