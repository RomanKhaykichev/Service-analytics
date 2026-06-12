import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { Shield, Users, UserPlus, AlertCircle, Pencil, Trash2, UserMinus, CalendarPlus, Banknote, Activity, BarChart3, ChevronUp, ChevronDown, Store, Inbox, Upload, RefreshCw } from "lucide-react";
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
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { apiGet, apiPatch, apiPost, apiDelete, apiPut } from "@/lib/api";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Checkbox } from "@/components/ui/checkbox";
import { AdminPanelTabs, type AdminPanelTab } from "@/components/admin/AdminPanelTabs";
import { UzumSyncLogsView } from "@/components/admin/UzumSyncLogsView";
import { ServicesView } from "@/components/dashboard/ServicesView";
import { ReportUploadDialog, type ReportUploadDialogHandle } from "@/components/dashboard/ReportUploadDialog";

function adminNormShopKey(s: string): string {
  return s.trim().replace(/\s+/g, " ").toUpperCase();
}

function adminNormPhone(s: string): string {
  return (s || "").replace(/\D+/g, "");
}

interface TenantRow {
  tenant_id: string;
  company_name?: string | null;
  owner_email?: string | null;
  phone?: string | null;
  created_at?: string | null;
  is_admin?: boolean;
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
  login_count?: number;
  has_uzum_api_key?: boolean;
}

interface TenantsResponse {
  tenants: TenantRow[];
  total_count: number;
}

interface DashboardFunnel {
  visited_site: number;
  tried: number;
  registered: number;
  with_shop: number;
  paid: number;
  conversion_pct: number;
}

interface DashboardFiles {
  total: number;
  training_opens: number;
  tariff_opens: number;
}

interface DashboardTotals {
  registered: number;
  paid_subscription: number;
  inactive_30d: number;
  returned_count: number;
  returned_pct: number;
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
  const [searchParams] = useSearchParams();
  const reportUploadRef = useRef<ReportUploadDialogHandle>(null);
  const [tenants, setTenants] = useState<TenantsResponse | null>(null);
  const [loadingTenants, setLoadingTenants] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [accessDenied, setAccessDenied] = useState(false);
  const [adminTab, setAdminTab] = useState<AdminPanelTab>("overview");
  const [search, setSearch] = useState("");
  const [planFilter, setPlanFilter] = useState<string>("all");
  const API_PAGE_SIZE = 100;
  const [sort, setSort] = useState("created_at");
  type TenantSortColumn = "created_at" | "phone" | "shops_count" | "plan" | "trial_days_left" | "paid_amount" | "last_login_at" | "login_count" | "imports_30d" | null;
  const [sortColumn, setSortColumn] = useState<TenantSortColumn>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc" | null>(null);
  const [tenantShops, setTenantShops] = useState<
    Record<string, { loading: boolean; error: string | null; names: string[]; allowedShops?: string[] | null }>
  >({});
  const [notesModal, setNotesModal] = useState<{ tenantId: string; notes: string } | null>(null);
  const [passwordModal, setPasswordModal] = useState<{ tenantId: string; newPassword: string } | null>(null);
  const [extendTrialModal, setExtendTrialModal] = useState<{ tenantId: string; days: number } | null>(null);
  const [paymentModal, setPaymentModal] = useState<{ tenantId: string; amount: number; plan: string } | null>(null);
  const [shopAllowTenantId, setShopAllowTenantId] = useState<string | null>(null);
  const [shopAllowLoading, setShopAllowLoading] = useState(false);
  const [shopAllowPayload, setShopAllowPayload] = useState<{
    all_shops: string[];
    selected: Set<string>;
    max_shops: number | null;
    uses_override: boolean;
  } | null>(null);
  const [confirmAction, setConfirmAction] = useState<null | { type: "disable" | "delete"; tenantId: string }>(null);
  const [syncingTenantId, setSyncingTenantId] = useState<string | null>(null);
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [dashboardMetrics, setDashboardMetrics] = useState<DashboardMetrics | null>(null);
  const [loadingMetrics, setLoadingMetrics] = useState(true);
  const [funnelMonth, setFunnelMonth] = useState<string>("all");
  const [supportTicketsTotal, setSupportTicketsTotal] = useState<number | null>(null);
  const [exportingUsers, setExportingUsers] = useState(false);

  const fetchSupportTicketsCount = useCallback(async () => {
    try {
      const res = await apiGet<{ total_count: number }>("/api/admin/support-tickets", {
        page: 1,
        page_size: 1,
        status: "open",
      });
      setSupportTicketsTotal(res.total_count ?? 0);
    } catch {
      setSupportTicketsTotal(null);
    }
  }, []);

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
        const baseParams: Record<string, string | number> = {
          page_size: API_PAGE_SIZE,
          sort,
        };
        const rawSearch = search.trim();
        const phoneDigits = adminNormPhone(rawSearch);
        const looksLikePhoneQuery = !!rawSearch && phoneDigits.length >= 4 && /^[\d\s()+-]+$/.test(rawSearch);
        // If it's a phone-like query, don't send it to API (API search may not support phone)
        // We'll fetch full list and filter client-side by phone digits.
        if (rawSearch && !looksLikePhoneQuery) baseParams.search = rawSearch;
        if (planFilter !== "all") {
          baseParams.plan = planFilter;
        }

        const firstPage = await apiGet<TenantsResponse>("/api/admin/tenants", {
          ...baseParams,
          page: 1,
        });

        const allTenants: TenantRow[] = [...(firstPage.tenants ?? [])];
        const totalCount = firstPage.total_count ?? allTenants.length;
        const totalPages = Math.max(1, Math.ceil(totalCount / API_PAGE_SIZE));

        for (let p = 2; p <= totalPages; p++) {
          const nextPage = await apiGet<TenantsResponse>("/api/admin/tenants", {
            ...baseParams,
            page: p,
          });
          if (nextPage.tenants?.length) {
            allTenants.push(...nextPage.tenants);
          }
        }

        setTenants({
          tenants: allTenants,
          total_count: totalCount,
        });
        void fetchSupportTicketsCount();
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
  }, [sort, search, planFilter, fetchSupportTicketsCount]);

  const loadTenantShops = useCallback(async (tenantId: string) => {
    setTenantShops((prev) => {
      const current = prev[tenantId];
      if (current?.loading || current?.names?.length) return prev;
      return { ...prev, [tenantId]: { loading: true, error: null, names: current?.names ?? [] } };
    });
    try {
      const res = await apiGet<{ tenant_id: string; shops: string[]; active_shop?: string | null; allowed_shops?: string[] | null }>(
        `/api/admin/tenants/${tenantId}/shops`
      );
      setTenantShops((prev) => ({
        ...prev,
        [tenantId]: { loading: false, error: null, names: res.shops ?? [], allowedShops: res.allowed_shops ?? null },
      }));
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setTenantShops((prev) => ({
        ...prev,
        [tenantId]: { loading: false, error: msg, names: prev[tenantId]?.names ?? [], allowedShops: prev[tenantId]?.allowedShops ?? null },
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
    if (row.is_admin) return -1;
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
        case "login_count":
          aVal = a.login_count ?? 0;
          bVal = b.login_count ?? 0;
          return sortDirection === "asc" ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number);
        case "imports_30d":
          aVal = a.imports_30d ?? 0;
          bVal = b.imports_30d ?? 0;
          return sortDirection === "asc" ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number);
        default:
          return 0;
      }
    });
  }, [tenants?.tenants, sortColumn, sortDirection]);

  const filteredTenants = useMemo(() => {
    const q = search.trim().toLowerCase();
    const list = sortedTenants;
    if (!q) return list;

    const qDigits = adminNormPhone(q);

    return list.filter((row) => {
      const hay = [
        row.company_name ?? "",
        row.owner_email ?? "",
        row.tenant_id ?? "",
      ]
        .join(" ")
        .toLowerCase();

      if (hay.includes(q)) return true;

      if (qDigits) {
        const phoneDigits = adminNormPhone(row.phone ?? "");
        if (phoneDigits && phoneDigits.includes(qDigits)) return true;
      }

      return false;
    });
  }, [sortedTenants, search]);

  const exportUsersToExcel = useCallback(async () => {
    if (exportingUsers) return;
    try {
      setExportingUsers(true);
      const XLSX = await import("xlsx");

      const rows = (filteredTenants ?? []).map((r) => ({
        "Tenant ID": r.tenant_id,
        "Компания": r.company_name ?? "",
        "Email": r.owner_email ?? "",
        "Телефон": r.phone ?? "",
        "Регистрация": r.created_at ?? "",
        "Тариф": r.plan ?? "",
        "Активен": r.is_active ? "Да" : "Нет",
        "Остаток дней": r.trial_days_left ?? "",
        "Оплачено": r.paid_amount ?? (r.paid ? "Да" : ""),
        "Магазинов": r.shops_count ?? "",
        "Импорты 30д": r.imports_30d ?? "",
        "Дата входа": r.last_login_at ?? "",
        "Вход": r.login_count ?? 0,
        "Notes": r.notes ?? "",
      }));

      const ws = XLSX.utils.json_to_sheet(rows);
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, "Users");

      const now = new Date();
      const stamp = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
      XLSX.writeFile(wb, `users_${stamp}.xlsx`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      toast.error(msg || "Не удалось выгрузить Excel");
    } finally {
      setExportingUsers(false);
    }
  }, [exportingUsers, filteredTenants]);

  useEffect(() => {
    const tab = searchParams.get("tab");
    if (tab === "overview" || tab === "uzum" || tab === "uzumUsers" || tab === "archive") {
      setAdminTab(tab);
    }
    if (tab === "archive" && searchParams.get("upload") === "guided") {
      queueMicrotask(() => reportUploadRef.current?.open("guided"));
    }
  }, [searchParams]);

  useEffect(() => {
    if (!accessDenied) {
      fetchTenants();
      fetchDashboardMetrics();
    }
  }, [accessDenied, fetchTenants, fetchDashboardMetrics]);

  useEffect(() => {
    if (!shopAllowTenantId) {
      setShopAllowPayload(null);
      return;
    }
    let cancelled = false;
    (async () => {
      setShopAllowLoading(true);
      try {
        const d = await apiGet<{
          all_shops: string[];
          selected: string[];
          max_shops: number | null;
          uses_override: boolean;
        }>(`/api/admin/tenants/${shopAllowTenantId}/shop-allowlist`);
        if (cancelled) return;
        const labelByNorm = new Map<string, string>();
        for (const l of d.all_shops) {
          labelByNorm.set(adminNormShopKey(l), l);
        }
        const selected = new Set<string>();
        for (const s of d.selected) {
          const canon = labelByNorm.get(adminNormShopKey(s));
          if (canon) selected.add(canon);
        }
        setShopAllowPayload({
          all_shops: d.all_shops,
          selected,
          max_shops: d.max_shops,
          uses_override: d.uses_override,
        });
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Не удалось загрузить список магазинов");
        if (!cancelled) setShopAllowTenantId(null);
      } finally {
        if (!cancelled) setShopAllowLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [shopAllowTenantId]);

  const toggleShopAllow = (label: string) => {
    setShopAllowPayload((p) => {
      if (!p) return p;
      const next = new Set(p.selected);
      const k = adminNormShopKey(label);
      const existing = [...next].find((x) => adminNormShopKey(x) === k);
      if (existing) {
        next.delete(existing);
      } else {
        if (p.max_shops != null && next.size >= p.max_shops) {
          toast.error(`Можно выбрать не более ${p.max_shops} магазинов`);
          return p;
        }
        const canon = p.all_shops.find((x) => adminNormShopKey(x) === k) ?? label;
        next.add(canon);
      }
      return { ...p, selected: next };
    });
  };

  const handleSaveShopAllow = async () => {
    if (!shopAllowTenantId || !shopAllowPayload) return;
    try {
      await apiPut(`/api/admin/tenants/${shopAllowTenantId}/shop-allowlist`, {
        shops: Array.from(shopAllowPayload.selected),
      });
      toast.success("Список разрешённых магазинов сохранён");
      setShopAllowTenantId(null);
      fetchTenants();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Ошибка сохранения");
    }
  };

  const handleResetShopAllow = async () => {
    if (!shopAllowTenantId) return;
    try {
      await apiPut(`/api/admin/tenants/${shopAllowTenantId}/shop-allowlist`, { shops: [] });
      toast.success("Используется автоматический список по тарифу");
      setShopAllowTenantId(null);
      fetchTenants();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Ошибка сброса");
    }
  };

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

  const handleRecordPayment = async () => {
    if (!paymentModal || paymentModal.amount <= 0) {
      toast.error("Укажите сумму больше 0");
      return;
    }
    try {
      const body: { amount: number; plan?: string } = { amount: paymentModal.amount };
      if (paymentModal.plan === "month_5" || paymentModal.plan === "month_10" || paymentModal.plan === "gold") {
        body.plan = paymentModal.plan;
      }
      await apiPost(`/api/admin/tenants/${paymentModal.tenantId}/payment`, body);
      setPaymentModal(null);
      toast.success(body.plan ? "Платёж записан. Пользователь переключен на тариф и получил 30 дней доступа." : "Платёж записан.");
      fetchTenants();
      fetchDashboardMetrics();
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      toast.error(msg || "Ошибка при записи платежа");
      setError(msg);
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

  const handleUzumSync = async (tenantId: string) => {
    setSyncingTenantId(tenantId);
    try {
      const res = await apiPost<{ ok: boolean; started?: boolean; message?: string }>(
        `/api/admin/tenants/${tenantId}/uzum-sync`,
        {},
      );
      toast.success(res.message ?? "Синхронизация запущена. Результат — во вкладке «Логи Uzum API».");
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      toast.error(msg || "Ошибка запуска синхронизации Uzum API");
      setError(msg);
    } finally {
      setSyncingTenantId(null);
    }
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

  const monthlyWithout2025 = useMemo(
    () => (dashboardMetrics?.monthly ?? []).filter((row) => !row.month.startsWith("2025")),
    [dashboardMetrics?.monthly]
  );

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

      <AdminPanelTabs activeTab={adminTab} onTabChange={setAdminTab} className="mb-6" />

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

      {!accessDenied && adminTab === "uzum" && <ServicesView />}

      {!accessDenied && adminTab === "uzumUsers" && <UzumSyncLogsView />}

      {!accessDenied && adminTab === "archive" && (
        <div className="space-y-4 max-w-lg">
          <p className="text-sm text-muted-foreground">{t("admin.archive.description")}</p>
          <div className="flex flex-col items-start gap-4">
            <button
              type="button"
              onClick={() => reportUploadRef.current?.open("guided")}
              className="inline-flex items-center gap-2 text-sm font-medium text-primary hover:underline underline-offset-2"
            >
              <Upload className="h-4 w-4 shrink-0" aria-hidden />
              {t("header.helpUploadReports")}
            </button>
            <ReportUploadDialog ref={reportUploadRef} showTrigger />
          </div>
        </div>
      )}

      {/* Метрики: воронка | всего + файлы | таблица по месяцам */}
      {!accessDenied && adminTab === "overview" && (
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
                      dashboardMetrics.funnel.with_shop,
                      dashboardMetrics.funnel.paid,
                      1
                    );
                    const rows: { n: number; label: string; pct: number | null; tooltip?: string }[] = [
                      { n: dashboardMetrics.funnel.visited_site, label: "Зашли на сайт", pct: null, tooltip: "Количество человек, зашедших на сайт (лендинг)" },
                      { n: dashboardMetrics.funnel.tried, label: "Попробовали", pct: dashboardMetrics.funnel.visited_site ? Math.round((dashboardMetrics.funnel.tried / dashboardMetrics.funnel.visited_site) * 100) : 0, tooltip: "Количество тех, кто нажал «Попробовать бесплатно» в промо-окне" },
                      { n: dashboardMetrics.funnel.registered, label: "Зарегистрировались", pct: dashboardMetrics.funnel.tried ? Math.round((dashboardMetrics.funnel.registered / dashboardMetrics.funnel.tried) * 100) : 0 },
                      { n: dashboardMetrics.funnel.with_shop, label: "Загрузили", pct: dashboardMetrics.funnel.registered ? Math.round((dashboardMetrics.funnel.with_shop / dashboardMetrics.funnel.registered) * 100) : 0, tooltip: "Клиенты с хотя бы одним магазином" },
                      { n: dashboardMetrics.funnel.paid, label: "Оплатили", pct: dashboardMetrics.funnel.with_shop ? Math.round((dashboardMetrics.funnel.paid / dashboardMetrics.funnel.with_shop) * 100) : 0 },
                    ];
                    return (
                      <>
                        {rows.map(({ n, label, pct, tooltip }, i) => (
                          <div key={i} className="flex items-center gap-2">
                            <span className="font-bold w-8 shrink-0">{n}</span>
                            <div className="flex-1 min-w-0 flex justify-center">
                              {tooltip ? (
                                <UITooltip>
                                  <TooltipTrigger asChild>
                                    <div
                                      className="h-8 flex items-center justify-center text-white text-sm font-medium rounded min-w-[60px] cursor-help"
                                      style={{
                                        background: "hsl(var(--primary))",
                                        width: `${Math.max((n / maxVal) * 100, n > 0 ? 8 : 0)}%`,
                                      }}
                                    >
                                      {label}
                                    </div>
                                  </TooltipTrigger>
                                  <TooltipContent side="top" className="max-w-xs">
                                    {tooltip}
                                  </TooltipContent>
                                </UITooltip>
                              ) : (
                                <div
                                  className="h-8 flex items-center justify-center text-white text-sm font-medium rounded min-w-[60px]"
                                  style={{
                                    background: "hsl(var(--primary))",
                                    width: `${Math.max((n / maxVal) * 100, n > 0 ? 8 : 0)}%`,
                                  }}
                                >
                                  {label}
                                </div>
                              )}
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

            {/* Колонка 2: Всего зарегистрировано (сверху) + Активности 30Д (снизу) */}
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
                      <p className="text-sm text-muted-foreground">
                        Платная подписка: <span className="font-bold text-foreground">{dashboardMetrics.totals.paid_subscription}</span>
                      </p>
                      <p className="text-sm text-muted-foreground">
                        Неактивны более 30 дней: <span className="font-bold text-foreground">{dashboardMetrics.totals.inactive_30d}</span>
                      </p>
                      <p className="text-sm text-muted-foreground">
                        Кол-во вернулись:{" "}
                        <span className="font-bold text-foreground">{dashboardMetrics.totals.returned_count}</span>{" "}
                        (<span className="font-bold text-foreground">{dashboardMetrics.totals.returned_pct}%</span>)
                      </p>
                    </>
                  ) : null}
                </CardContent>
              </Card>
              <Card className="flex-1 min-h-0 flex flex-col">
                <CardHeader className="pb-2 shrink-0">
                  <CardTitle className="text-sm font-medium uppercase tracking-wide text-muted-foreground flex items-center gap-2">
                    <Activity className="h-4 w-4 text-primary" />
                    Активности 30Д
                  </CardTitle>
                </CardHeader>
                <CardContent className="flex-1">
                  {loadingMetrics ? (
                    <Skeleton className="h-16 w-full" />
                  ) : dashboardMetrics ? (
                    <>
                      <p className="text-sm text-muted-foreground">
                        Загружено файлов: <span className="font-bold text-foreground">{dashboardMetrics.files.total}</span>
                      </p>
                      <p className="text-sm text-muted-foreground">
                        Открыли обучение: <span className="font-bold text-foreground">{dashboardMetrics.files.training_opens}</span>
                      </p>
                      <p className="text-sm text-muted-foreground">
                        Открыли тариф: <span className="font-bold text-foreground">{dashboardMetrics.files.tariff_opens}</span>
                      </p>
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
              <CardContent className="flex-1 min-h-0 flex flex-col p-0">
                {monthlyWithout2025.length > 0 ? (
                  <div className="overflow-y-auto overflow-x-hidden rounded-b-lg" style={{ maxHeight: "240px" }}>
                    <table className="w-full caption-bottom text-sm border-collapse">
                      <thead className="sticky top-0 z-10 bg-background [&_tr]:border-b">
                        <TableRow className="border-b py-0">
                          <TableHead className="px-2 py-1 text-xs h-auto">Месяц</TableHead>
                          <TableHead className="text-center px-2 py-1 text-xs h-auto">Прибыль</TableHead>
                          <TableHead
                            className="text-center px-2 py-1 text-xs h-auto"
                            title={t("admin.monthly.registrationsHelp")}
                          >
                            Регистрации
                          </TableHead>
                          <TableHead className="text-center px-2 py-1 text-xs h-auto">Оплат</TableHead>
                        </TableRow>
                      </thead>
                      <tbody className="[&_tr:last-child]:border-0">
                        {[...monthlyWithout2025].reverse().map((row) => (
                          <TableRow key={row.month} className="py-0">
                            <TableCell className="px-2 py-0.5 text-xs">{row.month_label}</TableCell>
                            <TableCell className="text-center px-2 py-0.5 text-xs">
                              {row.profit > 0 ? Number(row.profit).toLocaleString("ru-RU", { maximumFractionDigits: 0 }) : "0"}
                            </TableCell>
                            <TableCell className="text-center px-2 py-0.5 text-xs">{row.registrations}</TableCell>
                            <TableCell className="text-center px-2 py-0.5 text-xs">{row.payments}</TableCell>
                          </TableRow>
                        ))}
                      </tbody>
                      <tfoot className="sticky bottom-0 z-10 bg-muted/50 border-t [&_tr]:border-0">
                        <TableRow className="font-semibold bg-muted/50 py-0 border-0">
                          <TableCell className="px-2 py-0.5 text-xs">Всего</TableCell>
                          <TableCell className="text-center px-2 py-0.5 text-xs">
                            {monthlyWithout2025.reduce((s, r) => s + r.profit, 0).toLocaleString("ru-RU", { maximumFractionDigits: 0 })}
                          </TableCell>
                          <TableCell className="text-center px-2 py-0.5 text-xs">
                            {monthlyWithout2025.reduce((s, r) => s + r.registrations, 0)}
                          </TableCell>
                          <TableCell className="text-center px-2 py-0.5 text-xs">
                            {monthlyWithout2025.reduce((s, r) => s + r.payments, 0)}
                          </TableCell>
                        </TableRow>
                      </tfoot>
                    </table>
                  </div>
                ) : (
                  <div className="p-4 text-sm text-muted-foreground">
                    Нет данных
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* График Аналитика подписок: доход (столбцы) + подписчики (линия) */}
          {monthlyWithout2025.length > 0 && (
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
                    data={[...monthlyWithout2025].reverse()}
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

      {/* Таблица Пользователи */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5 text-primary" />
            Пользователи {tenants != null ? `(${tenants.total_count})` : ""}
          </CardTitle>
          <div className="flex flex-wrap gap-2 mt-2">
            <Input
              placeholder="Поиск (email, имя, ID, телефон)..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
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
                <SelectItem value="gold">Gold</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" asChild className="shrink-0">
              <Link to="/admin/appeals" className="inline-flex items-center gap-2">
                <Inbox className="h-4 w-4" />
                Обращения
                {supportTicketsTotal != null ? (
                  <span className="tabular-nums text-muted-foreground">({supportTicketsTotal})</span>
                ) : null}
              </Link>
            </Button>
            <Button
              type="button"
              variant="outline"
              className="shrink-0 ml-auto"
              onClick={exportUsersToExcel}
              disabled={exportingUsers || loadingTenants || !tenants}
              title="Выгрузить список пользователей в Excel"
            >
              {exportingUsers ? "Выгрузка…" : "Выгрузить Excel"}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {loadingTenants ? (
            <Skeleton className="h-64 w-full" />
          ) : tenants ? (
            <>
              <div
                className={cn(
                  "-mx-1 w-full min-w-0 max-w-full",
                  filteredTenants.length > 10
                    ? "max-h-[min(70vh,34rem)] sm:max-h-[min(75vh,40rem)] lg:max-h-[min(78vh,46rem)] overflow-auto"
                    : "overflow-auto",
                  "overscroll-contain touch-pan-x touch-pan-y [scrollbar-gutter:stable]"
                )}
              >
                <Table
                  wrapperClassName="overflow-visible min-w-0"
                  className={cn(
                    "w-full min-w-[1820px] table-fixed",
                    "[&_th]:h-9 [&_th]:py-1.5 [&_th]:px-2 [&_td]:py-1.5 [&_td]:px-2",
                    "[&_th]:align-middle [&_td]:align-middle",
                    "[&_thead_th]:whitespace-nowrap",
                    "[&_tbody_td]:whitespace-nowrap",
                    "[&_tbody_td:first-child]:whitespace-normal",
                    "[&_thead_th]:sticky [&_thead_th]:top-0 [&_thead_th]:z-20",
                    "[&_thead_th]:border-b [&_thead_th]:border-border [&_thead_th]:bg-card/95 [&_thead_th]:backdrop-blur-sm"
                  )}
                >
                <TableHeader>
                  <TableRow>
                    <TableHead className="sticky left-0 z-40 bg-card border-r border-border w-[220px]">Аккаунт</TableHead>
                    <TableHead className="text-center w-[5.5rem]">
                      <button
                        type="button"
                        onClick={() => handleTenantSort("created_at")}
                        className="inline-flex items-center justify-center gap-0.5 hover:text-foreground transition-colors w-full whitespace-nowrap"
                      >
                        Регистрация
                        <span className="flex flex-col">
                          <ChevronUp className={cn("h-3 w-3 -mb-1", sortColumn === "created_at" && sortDirection === "asc" ? "text-primary" : "text-muted-foreground/50")} />
                          <ChevronDown className={cn("h-3 w-3", sortColumn === "created_at" && sortDirection === "desc" ? "text-primary" : "text-muted-foreground/50")} />
                        </span>
                      </button>
                    </TableHead>
                    <TableHead className="text-center w-[7.5rem]">
                      <button type="button" onClick={() => handleTenantSort("phone")} className="inline-flex items-center justify-center gap-0.5 hover:text-foreground transition-colors w-full whitespace-nowrap">
                        Телефон
                        <span className="flex flex-col">
                          <ChevronUp className={cn("h-3 w-3 -mb-1", sortColumn === "phone" && sortDirection === "asc" ? "text-primary" : "text-muted-foreground/50")} />
                          <ChevronDown className={cn("h-3 w-3", sortColumn === "phone" && sortDirection === "desc" ? "text-primary" : "text-muted-foreground/50")} />
                        </span>
                      </button>
                    </TableHead>
                    <TableHead className="text-center w-[4.5rem]">
                      <button type="button" onClick={() => handleTenantSort("shops_count")} className="inline-flex items-center justify-center gap-0.5 hover:text-foreground transition-colors w-full whitespace-nowrap">
                        Магазин
                        <span className="flex flex-col">
                          <ChevronUp className={cn("h-3 w-3 -mb-1", sortColumn === "shops_count" && sortDirection === "asc" ? "text-primary" : "text-muted-foreground/50")} />
                          <ChevronDown className={cn("h-3 w-3", sortColumn === "shops_count" && sortDirection === "desc" ? "text-primary" : "text-muted-foreground/50")} />
                        </span>
                      </button>
                    </TableHead>
                    <TableHead className="text-center w-[6.5rem]">
                      <button type="button" onClick={() => handleTenantSort("plan")} className="inline-flex items-center justify-center gap-0.5 hover:text-foreground transition-colors w-full whitespace-nowrap">
                        Тариф
                        <span className="flex flex-col">
                          <ChevronUp className={cn("h-3 w-3 -mb-1", sortColumn === "plan" && sortDirection === "asc" ? "text-primary" : "text-muted-foreground/50")} />
                          <ChevronDown className={cn("h-3 w-3", sortColumn === "plan" && sortDirection === "desc" ? "text-primary" : "text-muted-foreground/50")} />
                        </span>
                      </button>
                    </TableHead>
                    <TableHead className="text-center w-[5.5rem]">
                      <button type="button" title="Статус подписки" onClick={() => handleTenantSort("trial_days_left")} className="inline-flex items-center justify-center gap-0.5 hover:text-foreground transition-colors w-full whitespace-nowrap">
                        Статус
                        <span className="flex flex-col">
                          <ChevronUp className={cn("h-3 w-3 -mb-1", sortColumn === "trial_days_left" && sortDirection === "asc" ? "text-primary" : "text-muted-foreground/50")} />
                          <ChevronDown className={cn("h-3 w-3", sortColumn === "trial_days_left" && sortDirection === "desc" ? "text-primary" : "text-muted-foreground/50")} />
                        </span>
                      </button>
                    </TableHead>
                    <TableHead className="text-center w-[5rem]">
                      <button type="button" title="Остаток дней" onClick={() => handleTenantSort("trial_days_left")} className="inline-flex items-center justify-center gap-0.5 hover:text-foreground transition-colors w-full whitespace-nowrap">
                        Дней
                        <span className="flex flex-col">
                          <ChevronUp className={cn("h-3 w-3 -mb-1", sortColumn === "trial_days_left" && sortDirection === "asc" ? "text-primary" : "text-muted-foreground/50")} />
                          <ChevronDown className={cn("h-3 w-3", sortColumn === "trial_days_left" && sortDirection === "desc" ? "text-primary" : "text-muted-foreground/50")} />
                        </span>
                      </button>
                    </TableHead>
                    <TableHead className="text-center w-[5.5rem]">
                      <button type="button" onClick={() => handleTenantSort("paid_amount")} className="inline-flex items-center justify-center gap-0.5 hover:text-foreground transition-colors w-full whitespace-nowrap">
                        Оплачено
                        <span className="flex flex-col">
                          <ChevronUp className={cn("h-3 w-3 -mb-1", sortColumn === "paid_amount" && sortDirection === "asc" ? "text-primary" : "text-muted-foreground/50")} />
                          <ChevronDown className={cn("h-3 w-3", sortColumn === "paid_amount" && sortDirection === "desc" ? "text-primary" : "text-muted-foreground/50")} />
                        </span>
                      </button>
                    </TableHead>
                    <TableHead className="text-center w-[6rem]">
                      <button type="button" onClick={() => handleTenantSort("last_login_at")} className="inline-flex items-center justify-center gap-0.5 hover:text-foreground transition-colors w-full whitespace-nowrap">
                        Дата входа
                        <span className="flex flex-col">
                          <ChevronUp className={cn("h-3 w-3 -mb-1", sortColumn === "last_login_at" && sortDirection === "asc" ? "text-primary" : "text-muted-foreground/50")} />
                          <ChevronDown className={cn("h-3 w-3", sortColumn === "last_login_at" && sortDirection === "desc" ? "text-primary" : "text-muted-foreground/50")} />
                        </span>
                      </button>
                    </TableHead>
                    <TableHead className="text-center w-[3.5rem]">
                      <button type="button" onClick={() => handleTenantSort("login_count")} className="inline-flex items-center justify-center gap-0.5 hover:text-foreground transition-colors w-full whitespace-nowrap">
                        Вход
                        <span className="flex flex-col">
                          <ChevronUp className={cn("h-3 w-3 -mb-1", sortColumn === "login_count" && sortDirection === "asc" ? "text-primary" : "text-muted-foreground/50")} />
                          <ChevronDown className={cn("h-3 w-3", sortColumn === "login_count" && sortDirection === "desc" ? "text-primary" : "text-muted-foreground/50")} />
                        </span>
                      </button>
                    </TableHead>
                    <TableHead className="text-center w-[5.5rem]">
                      <button type="button" title="Импорты за 30 дней" onClick={() => handleTenantSort("imports_30d")} className="inline-flex items-center justify-center gap-0.5 hover:text-foreground transition-colors w-full whitespace-nowrap">
                        Импорты
                        <span className="flex flex-col">
                          <ChevronUp className={cn("h-3 w-3 -mb-1", sortColumn === "imports_30d" && sortDirection === "asc" ? "text-primary" : "text-muted-foreground/50")} />
                          <ChevronDown className={cn("h-3 w-3", sortColumn === "imports_30d" && sortDirection === "desc" ? "text-primary" : "text-muted-foreground/50")} />
                        </span>
                      </button>
                    </TableHead>
                    <TableHead className="text-center w-[4.5rem]">Notes</TableHead>
                    <TableHead className="text-center w-[13rem]">Действия</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody className="[&_tr]:bg-card">
                  {filteredTenants.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={13} className="text-center text-muted-foreground">
                        Нет тенантов
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredTenants.map((row) => (
                      <TableRow key={row.tenant_id}>
                        <TableCell className="sticky left-0 z-10 bg-card border-r border-border w-[220px]">
                          <div className="font-medium truncate">{row.company_name || row.owner_email || row.tenant_id.slice(0, 8)}</div>
                          {row.owner_email && (
                            <div className="text-xs text-muted-foreground truncate">{row.owner_email}</div>
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
                                  (tenantShops[row.tenant_id]?.names?.length ? (
                                    tenantShops[row.tenant_id].names.map((name, idx) => {
                                      const allowedShops = tenantShops[row.tenant_id]?.allowedShops ?? [];
                                      const isAllowed = allowedShops.includes(name);
                                      return (
                                        <span key={`${name}-${idx}`}>
                                          {isAllowed ? <span className="font-bold">{name}</span> : name}
                                          {idx < tenantShops[row.tenant_id].names.length - 1 ? <br /> : null}
                                        </span>
                                      );
                                    })
                                  ) : (
                                    "Магазины не найдены"
                                  ))}
                              </TooltipContent>
                            </UITooltip>
                          ) : (
                            "—"
                          )}
                        </TableCell>
                        <TableCell className="text-center">
                          {(() => {
                            if (row.is_admin) {
                              return (
                                <span
                                  className="inline-block rounded-full px-2 py-0.5 text-xs font-medium bg-gradient-to-br from-[#e8e9ec] via-[#cfd1d9] to-[#9ca3af] text-slate-900 border border-slate-400/60 shadow-md shadow-slate-500/25"
                                >
                                  Admin
                                </span>
                              );
                            }
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
                                className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${pillClass}`}
                              >
                                {label}
                              </span>
                            );
                          })()}
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge
                            variant="secondary"
                            className={cn(
                              "text-xs py-0 px-2",
                              row.is_admin
                                ? "bg-green-500 text-white"
                                : row.trial_days_left != null && row.trial_days_left > 0
                                ? "bg-green-500 text-white"
                                : "bg-red-500 text-white"
                            )}
                          >
                            {row.is_admin
                              ? t("profile.active")
                              : row.trial_days_left != null && row.trial_days_left > 0
                              ? t("profile.active")
                              : t("profile.inactive")}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-center font-medium">
                          {row.is_admin ? "—" : row.trial_days_left != null ? row.trial_days_left : "—"}
                        </TableCell>
                        <TableCell className="text-center">
                          {row.paid_amount != null && row.paid_amount !== 0
                            ? Number(row.paid_amount).toLocaleString("ru-RU", { minimumFractionDigits: 0, maximumFractionDigits: 2 })
                            : row.paid
                              ? "Да"
                              : "—"}
                        </TableCell>
                        <TableCell className="text-center">{row.last_login_at ? row.last_login_at.slice(0, 10) : "—"}</TableCell>
                        <TableCell className="text-center font-medium">{row.login_count ?? 0}</TableCell>
                        <TableCell className="text-center font-medium">{row.imports_30d}</TableCell>
                        <TableCell className="text-center">
                          {row.is_admin ? (
                            "—"
                          ) : row.notes && row.notes.trim() ? (
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
                          {row.is_admin || (row.owner_email && row.owner_email === user?.email) ? (
                            "—"
                          ) : (
                            <div className="flex flex-nowrap gap-0.5 justify-center items-center">
                              {row.is_active ? (
                                <UITooltip>
                                  <TooltipTrigger asChild>
                                    <Button
                                      size="icon"
                                      variant="ghost"
                                      className="h-7 w-7"
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
                                      className="h-7 w-7 text-destructive bg-destructive/10 hover:bg-destructive/20 hover:text-destructive"
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
                                    className="h-7 w-7"
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
                                    className="h-7 w-7"
                                    onClick={() => setShopAllowTenantId(row.tenant_id)}
                                  >
                                    <Store className="h-4 w-4" />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>Разрешённые магазины</TooltipContent>
                              </UITooltip>
                              {row.has_uzum_api_key ? (
                                <UITooltip>
                                  <TooltipTrigger asChild>
                                    <Button
                                      size="icon"
                                      variant="ghost"
                                      className="h-7 w-7"
                                      disabled={syncingTenantId === row.tenant_id}
                                      onClick={() => void handleUzumSync(row.tenant_id)}
                                    >
                                      <RefreshCw
                                        className={cn(
                                          "h-4 w-4",
                                          syncingTenantId === row.tenant_id && "animate-spin",
                                        )}
                                      />
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    {t("admin.tooltip.uzumSync")}
                                  </TooltipContent>
                                </UITooltip>
                              ) : null}
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Button
                                    size="icon"
                                    variant="ghost"
                                    className="h-7 w-7"
                                    onClick={() =>
                                      setPaymentModal({
                                        tenantId: row.tenant_id,
                                        amount: 0,
                                        plan: "",
                                      })
                                    }
                                  >
                                    <Banknote className="h-4 w-4" />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>
                                  {t("admin.tooltip.recordPayment")}
                                </TooltipContent>
                              </UITooltip>
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <Button
                                    size="icon"
                                    variant="ghost"
                                    className="h-7 w-7"
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
                                    className="h-7 w-7 text-destructive hover:text-destructive hover:bg-destructive/10"
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
            </>
          ) : null}
        </CardContent>
      </Card>
        </>
      )}

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

      <Dialog open={!!paymentModal} onOpenChange={(open) => !open && setPaymentModal(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Записать платёж</DialogTitle>
            <p className="text-sm text-muted-foreground">Сумма и тариф. При выборе тарифа пользователь переключится на него и получит 30 дней доступа.</p>
          </DialogHeader>
          {paymentModal && (
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Сумма (сум)</label>
                <Input
                  type="number"
                  min={0}
                  step={0.01}
                  value={paymentModal.amount || ""}
                  onChange={(e) => {
                    const v = parseFloat(e.target.value);
                    setPaymentModal((p) => p ? { ...p, amount: Number.isNaN(v) ? 0 : v } : null);
                  }}
                  placeholder="0"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Тариф (переключить пользователя)</label>
                <Select
                  value={paymentModal.plan || "none"}
                  onValueChange={(v) => setPaymentModal((p) => p ? { ...p, plan: v === "none" ? "" : v } : null)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Не менять тариф" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Не менять тариф</SelectItem>
                    <SelectItem value="month_5">Month 5</SelectItem>
                    <SelectItem value="month_10">Month 10</SelectItem>
                    <SelectItem value="gold">Gold</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setPaymentModal(null)}>Отмена</Button>
            <Button onClick={handleRecordPayment} disabled={!paymentModal || paymentModal.amount <= 0}>
              Записать платёж
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={!!shopAllowTenantId}
        onOpenChange={(open) => {
          if (!open) setShopAllowTenantId(null);
        }}
      >
        <DialogContent className="max-w-md max-h-[85vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>Разрешённые магазины</DialogTitle>
            <p className="text-sm text-muted-foreground">
              Отметьте магазины, которые видит пользователь в сервисе и которые учитываются при загрузке отчётов с колонкой «Магазин».
              Кнопка «По тарифу (авто)» сбрасывает ручной список.
            </p>
          </DialogHeader>
          {shopAllowLoading || !shopAllowPayload ? (
            <Skeleton className="h-40 w-full shrink-0" />
          ) : (
            <>
              <p className="text-xs text-muted-foreground shrink-0">
                {shopAllowPayload.max_shops != null
                  ? `Лимит тарифа: до ${shopAllowPayload.max_shops} магазинов.`
                  : "По тарифу без лимита по количеству магазинов."}{" "}
                {shopAllowPayload.uses_override
                  ? "Сейчас задан явный список."
                  : "Сейчас: первые магазины по правилам тарифа."}
              </p>
              <div className="flex-1 min-h-[200px] max-h-[50vh] overflow-y-auto space-y-2 border rounded-md p-3">
                {shopAllowPayload.all_shops.length === 0 ? (
                  <p className="text-sm text-muted-foreground">У пользователя пока нет магазинов в загруженных данных.</p>
                ) : (
                  shopAllowPayload.all_shops.map((name) => (
                    <label key={name} className="flex items-start gap-2 text-sm cursor-pointer">
                      <Checkbox
                        className="mt-0.5"
                        checked={shopAllowPayload.selected.has(name)}
                        onCheckedChange={() => toggleShopAllow(name)}
                      />
                      <span className="break-all leading-snug">{name}</span>
                    </label>
                  ))
                )}
              </div>
            </>
          )}
          <DialogFooter className="flex-col sm:flex-row gap-2 sm:justify-between">
            <Button variant="outline" onClick={handleResetShopAllow} disabled={!shopAllowTenantId || shopAllowLoading}>
              По тарифу (авто)
            </Button>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setShopAllowTenantId(null)}>Закрыть</Button>
              <Button onClick={handleSaveShopAllow} disabled={shopAllowLoading || !shopAllowPayload}>
                Сохранить
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </MainLayout>
  );
}
