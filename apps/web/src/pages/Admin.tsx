import { useState, useEffect, useCallback } from "react";
import { Shield, Users, UserPlus, Activity, Upload, AlertCircle, BarChart3, Pencil, Trash2, UserMinus, CalendarPlus } from "lucide-react";
import { Tooltip as UITooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { MainLayout } from "@/components/layout/MainLayout";
import { Breadcrumb } from "@/components/shared/Breadcrumb";
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
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import {
  BarChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ComposedChart,
  LabelList,
} from "recharts";
import { apiGet, apiPatch, apiPost, apiDelete } from "@/lib/api";
import { toast } from "sonner";

const fmt = (v: number | null | undefined) => (v != null ? String(v) : "—");

interface AdminKPIs {
  active_customers_mau_30d?: number | null;
  new_signups_7d?: number | null;
  new_signups_30d?: number | null;
  activated_pct?: number | null;
  paid_count?: number | null;
  trial_count?: number | null;
  expired_count?: number | null;
  mrr?: number | null;
  revenue_30d?: number | null;
  imports_24h?: number | null;
  import_success_rate_7d?: number | null;
  queue_pending?: number | null;
  queue_running?: number | null;
  queue_failed?: number | null;
  oldest_pending_minutes?: number | null;
  api_errors_5xx_24h?: number | null;
}

interface AdminOverview {
  kpis: AdminKPIs;
  registrations_per_day: Array<{ date: string; count: number }>;
  visits_per_day: Array<{ date: string; count: number }>;
  total_visits_per_day?: Array<{ date: string; count: number }>;
  imports_per_day: Array<{ date: string; success: number; failed: number }>;
  data_freshness_buckets: Array<{ bucket: string; count: number }>;
  subscription_analytics?: Array<{ month: string; active_users: number; revenue: number }>;
}

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

export default function Admin() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [tenants, setTenants] = useState<TenantsResponse | null>(null);
  const [loadingOverview, setLoadingOverview] = useState(true);
  const [loadingTenants, setLoadingTenants] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [accessDenied, setAccessDenied] = useState(false);
  const [search, setSearch] = useState("");
  const [planFilter, setPlanFilter] = useState<string>("all");
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [sort, setSort] = useState("created_at");
  const [notesModal, setNotesModal] = useState<{ tenantId: string; notes: string } | null>(null);
  const [passwordModal, setPasswordModal] = useState<{ tenantId: string; newPassword: string } | null>(null);
  const [extendTrialModal, setExtendTrialModal] = useState<{ tenantId: string; days: number } | null>(null);
  // Период для графика регистраций/заходов (по умолчанию 30 дней)
  const [chartPeriodDays, setChartPeriodDays] = useState(30);
  const [chartFrom, setChartFrom] = useState<string>(() => {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    return d.toISOString().slice(0, 10);
  });
  const [chartTo, setChartTo] = useState<string>(() => new Date().toISOString().slice(0, 10));
  const [subscriptionChartPeriod, setSubscriptionChartPeriod] = useState<"day" | "week" | "month">("month");

  const fetchOverview = useCallback(async () => {
    setLoadingOverview(true);
    setError(null);
    setAccessDenied(false);
    try {
      const data = await apiGet<AdminOverview>("/api/admin/overview", {
        from: chartFrom,
        to: chartTo,
        subscription_period: subscriptionChartPeriod,
      });
      setOverview(data);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      if (msg.includes("403") || msg.includes("Admin")) {
        setAccessDenied(true);
      } else {
        setError(msg);
      }
    } finally {
      setLoadingOverview(false);
    }
  }, [chartFrom, chartTo, subscriptionChartPeriod]);

  const fetchTenants = useCallback(async () => {
    setLoadingTenants(true);
    setError(null);
    try {
      const params: Record<string, string | number> = {
        page,
        page_size: pageSize,
        sort,
      };
      if (search.trim()) params.search = search.trim();
      if (planFilter !== "all") params.plan = planFilter;
      const data = await apiGet<TenantsResponse>("/api/admin/tenants", params);
      setTenants(data);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      if (!msg.includes("403")) setError(msg);
    } finally {
      setLoadingTenants(false);
    }
  }, [page, pageSize, sort, search, planFilter]);

  useEffect(() => {
    fetchOverview();
  }, [fetchOverview]);

  const applyChartPeriod = (days: number) => {
    setChartPeriodDays(days);
    const to = new Date();
    const from = new Date(to);
    from.setDate(from.getDate() - days);
    setChartFrom(from.toISOString().slice(0, 10));
    setChartTo(to.toISOString().slice(0, 10));
  };

  useEffect(() => {
    if (!accessDenied) fetchTenants();
  }, [accessDenied, fetchTenants]);

  const handleDisable = async (tenantId: string) => {
    if (!confirm("Отключить тенанта? Пользователь не сможет входить.")) return;
    try {
      await apiPost(`/api/admin/tenants/${tenantId}/disable`, {});
      fetchTenants();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
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
    if (!confirm("Удалить аккаунт и все загруженные данные безвозвратно?")) return;
    try {
      await apiDelete(`/api/admin/tenants/${tenantId}`);
      fetchTenants();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  if (accessDenied) {
    return (
      <MainLayout>
        <Breadcrumb items={[{ label: t("header.adminPanel") }]} />
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

  return (
    <MainLayout>
      <Breadcrumb items={[{ label: t("header.adminPanel") }]} />
      <div className="mb-6 flex items-center gap-2">
        <Shield className="h-7 w-7" />
        <h1 className="text-2xl font-bold text-foreground">{t("header.adminPanel")}</h1>
      </div>
      <p className="text-muted-foreground mb-6">Мониторинг клиентов, импортов и здоровья системы.</p>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Ошибка</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* KPI cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4 mb-6">
        {loadingOverview ? (
          Array.from({ length: 8 }).map((_, i) => (
            <Card key={i}>
              <CardHeader className="pb-2">
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-16" />
              </CardContent>
            </Card>
          ))
        ) : overview ? (
          <>
            <Card>
              <CardHeader className="pb-2 flex flex-row items-center gap-2">
                <Users className="h-4 w-4" />
                <CardTitle className="text-sm font-medium">Active (MAU 30d)</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{fmt(overview.kpis.active_customers_mau_30d)}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2 flex flex-row items-center gap-2">
                <UserPlus className="h-4 w-4" />
                <CardTitle className="text-sm font-medium">Signups 7d / 30d</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">
                  {fmt(overview.kpis.new_signups_7d)} / {fmt(overview.kpis.new_signups_30d)}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Activated %</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">
                  {overview.kpis.activated_pct != null ? `${overview.kpis.activated_pct.toFixed(1)}%` : "—"}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Paid / Trial / Expired</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-lg font-bold">
                  {fmt(overview.kpis.paid_count)} / {fmt(overview.kpis.trial_count)} / {fmt(overview.kpis.expired_count)}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2 flex flex-row items-center gap-2">
                <Upload className="h-4 w-4" />
                <CardTitle className="text-sm font-medium">Импорты за 24ч</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{fmt(overview.kpis.imports_24h)}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Успешность импорта 7д %</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">
                  {overview.kpis.import_success_rate_7d != null
                    ? `${overview.kpis.import_success_rate_7d.toFixed(1)}%`
                    : "—"}
                </p>
              </CardContent>
            </Card>
          </>
        ) : null}
      </div>

      {/* Charts */}
      {overview && !loadingOverview && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Регистрации и заходы по дням
              </CardTitle>
              <div className="flex gap-1">
                {[7, 30, 90].map((d) => (
                  <Button
                    key={d}
                    size="sm"
                    variant={chartPeriodDays === d ? "default" : "outline"}
                    onClick={() => applyChartPeriod(d)}
                  >
                    {d} дн.
                  </Button>
                ))}
              </div>
            </CardHeader>
            <CardContent>
              {(() => {
                const regMap = new Map(overview.registrations_per_day.map((r) => [r.date, r.count]));
                const visMap = new Map((overview.visits_per_day || []).map((v) => [v.date, v.count]));
                const totalVisMap = new Map((overview.total_visits_per_day || []).map((v) => [v.date, v.count]));
                const allDates = new Set([...regMap.keys(), ...visMap.keys(), ...totalVisMap.keys()]);
                const merged = Array.from(allDates)
                  .sort()
                  .map((date) => ({
                    date,
                    registrations: regMap.get(date) ?? 0,
                    visits: visMap.get(date) ?? 0,
                    total_visits: totalVisMap.get(date) ?? 0,
                  }));
                return merged.length > 0 ? (
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={merged} margin={{ top: 20, right: 8, left: 4, bottom: 4 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                      <YAxis allowDecimals={false} />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="registrations" fill="hsl(var(--primary))" name="Регистрации" barSize={28}>
                        <LabelList dataKey="registrations" position="top" fontSize={10} formatter={(v: number) => (v > 0 ? v : "")} />
                      </Bar>
                      <Bar dataKey="visits" fill="hsl(var(--chart-2))" name="Зашли на сайт" barSize={28}>
                        <LabelList dataKey="visits" position="top" fontSize={10} formatter={(v: number) => (v > 0 ? v : "")} />
                      </Bar>
                      <Bar dataKey="total_visits" fill="hsl(var(--chart-3))" name="Посещения" barSize={28}>
                        <LabelList dataKey="total_visits" position="top" fontSize={10} formatter={(v: number) => (v > 0 ? v : "")} />
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-muted-foreground text-sm">Нет данных за выбранный период</p>
                );
              })()}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                Импорты по дням
              </CardTitle>
            </CardHeader>
            <CardContent>
              {overview.imports_per_day.length > 0 ? (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={overview.imports_per_day}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                    <YAxis allowDecimals={false} />
                    <Tooltip
                      formatter={(value: number, name: string) => [value, name]}
                      labelFormatter={(label) => `Дата: ${label}`}
                    />
                    <Legend />
                    <Bar dataKey="success" stackId="a" fill="#22c55e" name="Успешно загружено" />
                    <Bar dataKey="failed" stackId="a" fill="#ef4444" name="Ошибка загрузки (error reading)" />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-muted-foreground text-sm">Нет данных</p>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Data freshness buckets */}
      {overview && overview.data_freshness_buckets.length > 0 && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Свежесть данных (дней назад)</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={overview.data_freshness_buckets}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="bucket" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="hsl(var(--chart-2))" name="Тенантов" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Аналитика подписок по месяцам */}
      {overview && (
        <Card className="mb-6">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-primary" />
              Аналитика подписок
            </CardTitle>
            <Select
              value={subscriptionChartPeriod}
              onValueChange={(v: "day" | "week" | "month") => {
                setSubscriptionChartPeriod(v);
              }}
            >
              <SelectTrigger className="w-[130px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="day">День</SelectItem>
                <SelectItem value="week">Неделя</SelectItem>
                <SelectItem value="month">Месяц</SelectItem>
              </SelectContent>
            </Select>
          </CardHeader>
          <CardContent>
            {(overview.subscription_analytics?.length ?? 0) > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <ComposedChart
                  data={overview.subscription_analytics}
                  margin={{ top: 8, right: 8, left: 4, bottom: 4 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                  <YAxis
                    yAxisId="left"
                    tick={{ fontSize: 10 }}
                    allowDecimals={false}
                    domain={(dataMin: number, dataMax: number) => [0, Math.max((dataMax ?? 0) + 1, 2)]}
                    name="Пользователи"
                  />
                  <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10 }} tickFormatter={(v) => (v >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `${(v / 1e3).toFixed(0)}k` : String(v))} />
                  <Tooltip formatter={(value: number, name: string) => [name === "Доход" ? Number(value).toLocaleString("ru-RU", { minimumFractionDigits: 0, maximumFractionDigits: 0 }) : value, name]} />
                  <Legend />
                  <Bar yAxisId="left" dataKey="active_users" fill="hsl(var(--primary))" name="Пользователи" barSize={24} radius={[2, 2, 0, 0]} />
                  <Line yAxisId="right" type="monotone" dataKey="revenue" stroke="hsl(var(--chart-2))" strokeWidth={2} name="Доход" dot={{ r: 3 }} />
                </ComposedChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-muted-foreground text-sm py-8">Нет данных</p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Tenants table */}
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
              onKeyDown={(e) => e.key === "Enter" && setPage(1) && fetchTenants()}
              className="max-w-xs"
            />
            <Select value={planFilter} onValueChange={setPlanFilter}>
              <SelectTrigger className="w-[120px]">
                <SelectValue placeholder="Plan" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Все</SelectItem>
                <SelectItem value="trial">Trial</SelectItem>
                <SelectItem value="paid">Paid</SelectItem>
                <SelectItem value="expired">Expired</SelectItem>
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
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Аккаунт</TableHead>
                    <TableHead className="text-center">Регистрация</TableHead>
                    <TableHead className="text-center">Телефон</TableHead>
                    <TableHead className="text-center">Магазин</TableHead>
                    <TableHead className="text-center">Тариф</TableHead>
                    <TableHead className="text-center">Статус подписки</TableHead>
                    <TableHead className="text-center">Остаток дней</TableHead>
                    <TableHead className="text-center">Оплачено</TableHead>
                    <TableHead className="text-center">Дата входа</TableHead>
                    <TableHead className="text-center">Импорты 30д</TableHead>
                    <TableHead className="text-center">Notes</TableHead>
                    <TableHead className="text-center">Действия</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tenants.tenants.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={12} className="text-center text-muted-foreground">
                        Нет тенантов
                      </TableCell>
                    </TableRow>
                  ) : (
                    tenants.tenants.map((row) => (
                      <TableRow key={row.tenant_id}>
                        <TableCell>
                          <div className="font-medium">{row.company_name || row.owner_email || row.tenant_id.slice(0, 8)}</div>
                          {row.owner_email && (
                            <div className="text-xs text-muted-foreground">{row.owner_email}</div>
                          )}
                        </TableCell>
                        <TableCell className="text-center">{row.created_at ?? "—"}</TableCell>
                        <TableCell className="text-center">{row.phone ?? "—"}</TableCell>
                        <TableCell className="text-center">{row.shops_count != null ? row.shops_count : "—"}</TableCell>
                        <TableCell className="text-center">{row.plan}</TableCell>
                        <TableCell className="text-center">—</TableCell>
                        <TableCell className="text-center">{row.trial_days_left != null ? row.trial_days_left : "—"}</TableCell>
                        <TableCell className="text-center">
                          {row.paid_amount != null && row.paid_amount !== 0
                            ? Number(row.paid_amount).toLocaleString("ru-RU", { minimumFractionDigits: 0, maximumFractionDigits: 2 })
                            : row.paid
                              ? "Да"
                              : "—"}
                        </TableCell>
                        <TableCell className="text-center">{row.last_login_at ? row.last_login_at.slice(0, 10) : "—"}</TableCell>
                        <TableCell className="text-center">{row.imports_30d} успешно, {row.failed_imports_30d} ошибок</TableCell>
                        <TableCell className="text-center">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => setNotesModal({ tenantId: row.tenant_id, notes: row.notes ?? "" })}
                          >
                            {row.notes ? (row.notes.length > 20 ? `${row.notes.slice(0, 20)}…` : row.notes) : "Edit"}
                          </Button>
                        </TableCell>
                        <TableCell className="text-center">
                          {row.owner_email && row.owner_email === user?.email ? (
                            "—"
                          ) : (
                            <div className="flex flex-wrap gap-1 justify-center items-center">
                              {row.is_active ? (
                                <UITooltip>
                                  <TooltipTrigger asChild>
                                    <Button size="icon" variant="ghost" className="h-8 w-8" onClick={() => handleDisable(row.tenant_id)}>
                                      <UserMinus className="h-4 w-4" />
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent>Отключить</TooltipContent>
                                </UITooltip>
                              ) : (
                                <UITooltip>
                                  <TooltipTrigger asChild>
                                    <Button size="icon" variant="ghost" className="h-8 w-8" onClick={() => handleEnable(row.tenant_id)}>
                                      <UserPlus className="h-4 w-4" />
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent>Включить</TooltipContent>
                                </UITooltip>
                              )}
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Button size="icon" variant="ghost" className="h-8 w-8" onClick={() => setExtendTrialModal({ tenantId: row.tenant_id, days: 7 })}>
                                    <CalendarPlus className="h-4 w-4" />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>Добавить дни триала</TooltipContent>
                              </UITooltip>
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Button size="icon" variant="ghost" className="h-8 w-8" onClick={() => setPasswordModal({ tenantId: row.tenant_id, newPassword: "" })}>
                                    <Pencil className="h-4 w-4" />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>Изменить / сбросить пароль</TooltipContent>
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
                                <TooltipContent>Удалить аккаунт и данные</TooltipContent>
                              </UITooltip>
                            </div>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
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
