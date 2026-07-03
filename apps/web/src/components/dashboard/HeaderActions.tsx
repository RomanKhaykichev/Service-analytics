import { useState, useEffect, useRef, useCallback } from "react";
import { Bell, HelpCircle, User, ChevronDown, LogOut, CreditCard, Globe, PlayCircle, MessageCircle, ShieldCheck, KeyRound, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { UzumApiConnectDialog, type UzumApiConnectDialogHandle } from "./UzumApiConnectDialog";
import { HelpConnectApiDialog, type HelpConnectApiDialogHandle } from "./HelpConnectApiDialog";
import { PricingDialog } from "./PricingDialog";
import { ProfileDialog } from "./ProfileDialog";
import { useNavigate, Link } from "react-router-dom";
import { useLanguage, type Language } from "@/contexts/LanguageContext";
import { useAuth } from "@/hooks/useAuth";
import { useStorageShops } from "@/hooks/useStorageShops";
import { apiGet } from "@/lib/api";
import { formatCurrency } from "@/lib/formatters";
import { toast } from "sonner";

const headerLanguages: { code: Language; label: string }[] = [
  { code: "ru", label: "Русский" },
  { code: "uz", label: "O'zbekcha" },
];

const DISMISSED_EXPENSE_NOTIFICATIONS_PREFIX = "dismissed_expense_notifications";

function getUserDisplayName(user: { full_name?: string; user_metadata?: { full_name?: string }; email?: string } | null): string {
  if (!user) return "Пользователь";
  if (user.full_name) return user.full_name;
  if (user.user_metadata?.full_name) return user.user_metadata.full_name;
  if (user.email) return user.email;
  return "Пользователь";
}

interface HeaderActionsProps {
  apiConnectRef?: React.RefObject<UzumApiConnectDialogHandle | null>;
}

interface ExpenseNotification {
  id: string;
  service: string;
  service_key?: string;
  service_number?: string | null;
  written_off_date: string | null;
  amount_sum: number;
}

interface ExpenseNotificationsResponse {
  items: ExpenseNotification[];
  count: number;
}

function formatNotificationDate(value: string | null): string {
  if (!value) return "—";
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("ru-RU");
}

function appendNotificationNumber(label: string, number?: string | null): string {
  return number ? `${label} № ${number}` : label;
}

function getExpenseNotificationService(notification: ExpenseNotification, language: Language): string {
  const labels: Record<string, { ru: string; uz: string }> = {
    storage_return: {
      ru: "Оплата за услуги хранения собранного возврата по накладной",
      uz: "Sonli yukxat boʻyicha yigʻilgan qaytarishni saqlash xizmatlari uchun toʻlov",
    },
    warehouse_return: {
      ru: "Обработка возврата со склада по накладной",
      uz: "Sonli yuk xati bo‘yicha ombordan qaytarishni qayta ishlash",
    },
    utilization_invoice: {
      ru: "Обработка накладной утилизации",
      uz: "Sonli yuk xati bo'yicha ombordan qaytarishni qayta ishlash",
    },
    fine_discrepancy: {
      ru: "Штраф за расхождения при приемке накладной",
      uz: "Qabuldagi tafovut uchun jarima",
    },
    fine: {
      ru: "Штраф",
      uz: "Jarima",
    },
  };

  const label = notification.service_key ? labels[notification.service_key] : undefined;
  if (!label) return notification.service;
  return appendNotificationNumber(label[language === "uz" ? "uz" : "ru"], notification.service_number);
}

function getDismissedExpenseNotificationsKey(userId: string): string {
  return `${DISMISSED_EXPENSE_NOTIFICATIONS_PREFIX}:${userId}`;
}

function readDismissedExpenseNotificationIds(userId: string): Set<string> {
  try {
    const raw = localStorage.getItem(getDismissedExpenseNotificationsKey(userId));
    if (!raw) return new Set();
    const parsed = JSON.parse(raw);
    return new Set(Array.isArray(parsed) ? parsed.filter((id): id is string => typeof id === "string") : []);
  } catch {
    return new Set();
  }
}

function writeDismissedExpenseNotificationIds(userId: string, ids: Set<string>): void {
  try {
    localStorage.setItem(getDismissedExpenseNotificationsKey(userId), JSON.stringify([...ids]));
  } catch {
    // If storage is unavailable, keep the UI-only removal for the current state.
  }
}

export function HeaderActions({ apiConnectRef: apiConnectRefProp }: HeaderActionsProps = {}) {
  const { t, language, setLanguage } = useLanguage();
  const { user, signOut } = useAuth();
  const { shops, loading: shopsLoading } = useStorageShops();
  const navigate = useNavigate();
  const [tariffOpen, setTariffOpen] = useState(false);
  const [extendTariffOpen, setExtendTariffOpen] = useState(false);
  const [extendVariant, setExtendVariant] = useState<"extend" | "expired">("extend");

  const handleSignOut = async () => {
    await signOut();
    toast.success(t('header.loggedOut'));
    navigate('/landing?auth=open');
  };
  const [profileOpen, setProfileOpen] = useState(false);
  const [expenseNotifications, setExpenseNotifications] = useState<ExpenseNotification[]>([]);
  const [expenseNotificationsCount, setExpenseNotificationsCount] = useState(0);
  const [expenseNotificationsLoading, setExpenseNotificationsLoading] = useState(false);
  const apiConnectRefInternal = useRef<UzumApiConnectDialogHandle>(null);
  const apiConnectRef = apiConnectRefProp ?? apiConnectRefInternal;
  const helpConnectApiRef = useRef<HelpConnectApiDialogHandle>(null);
  /** Чтобы не открывать снова при каждом refetch при 0 магазинах; сбрасывается при появлении магазина или новом монтировании шапки (новый «вход» на главную). */
  const noShopsGuidedOpenedThisMountRef = useRef(false);
  const displayName = getUserDisplayName(user);

  const validUntilLabel = (() => {
    if (user?.is_admin) {
      return null;
    }
    if (user?.trial_ends_at) {
      const d = new Date(user.trial_ends_at);
      if (!isNaN(d.getTime())) return d.toLocaleDateString("ru-RU");
    }
    if (typeof user?.trial_days_left === "number") {
      const d = new Date();
      d.setDate(d.getDate() + user.trial_days_left);
      return d.toLocaleDateString("ru-RU");
    }
    return null;
  })();
  const dateIsSoon =
    !user?.is_admin &&
    typeof user?.trial_days_left === "number" &&
    user.trial_days_left <= 3;

  const isTrialExpired =
    !!user &&
    !user.is_admin &&
    (user.plan ?? "trial").toLowerCase() !== "paid" &&
    user.trial_days_left != null &&
    user.trial_days_left <= 0;

  const loadExpenseNotifications = useCallback(async () => {
    if (!user?.id) {
      setExpenseNotifications([]);
      setExpenseNotificationsCount(0);
      return;
    }

    setExpenseNotificationsLoading(true);
    try {
      const data = await apiGet<ExpenseNotificationsResponse>("/api/notifications/expenses", { limit: 20 });
      const dismissedIds = readDismissedExpenseNotificationIds(user.id);
      const items = (data.items ?? []).filter((item) => !dismissedIds.has(item.id));
      const totalCount = data.count ?? data.items?.length ?? 0;
      setExpenseNotifications(items);
      setExpenseNotificationsCount(Math.max(0, totalCount - dismissedIds.size));
    } catch {
      setExpenseNotifications([]);
      setExpenseNotificationsCount(0);
    } finally {
      setExpenseNotificationsLoading(false);
    }
  }, [user?.id]);

  const dismissExpenseNotification = useCallback((id: string) => {
    if (!user?.id) return;

    const dismissedIds = readDismissedExpenseNotificationIds(user.id);
    dismissedIds.add(id);
    writeDismissedExpenseNotificationIds(user.id, dismissedIds);
    setExpenseNotifications((items) => items.filter((item) => item.id !== id));
    setExpenseNotificationsCount((count) => Math.max(0, count - 1));
  }, [user?.id]);

  useEffect(() => {
    void loadExpenseNotifications();
  }, [loadExpenseNotifications]);

  // Открываем окно «Тариф закончился» сразу после входа, если триал закончился
  useEffect(() => {
    if (isTrialExpired) {
      setExtendVariant("expired");
      setExtendTariffOpen(true);
    }
  }, [isTrialExpired]);

  // Появился хотя бы один магазин — снимаем блокировку повторного авто-открытия на этом монтировании (на случай снова пустых данных)
  useEffect(() => {
    if (shops.length > 0) {
      noShopsGuidedOpenedThisMountRef.current = false;
    }
  }, [shops.length]);

  // Нет магазинов в seller-storage: при каждом заходе на главную (монтирование шапки) показываем инструкцию, пока магазинов 0
  useEffect(() => {
    if (!user || user.is_admin) return;
    if (isTrialExpired) return;
    if (shopsLoading) return;
    if (shops.length > 0) return;
    if (noShopsGuidedOpenedThisMountRef.current) return;
    noShopsGuidedOpenedThisMountRef.current = true;
    queueMicrotask(() => {
      apiConnectRef.current?.open();
    });
  }, [user?.id, user?.is_admin, isTrialExpired, shopsLoading, shops.length]);

  return (
    <div className="flex items-center gap-4 sm:gap-5">
      {/* Report Upload */}
      <UzumApiConnectDialog
        ref={apiConnectRef}
        disabled={isTrialExpired}
        onOpenHelpGuide={() => helpConnectApiRef.current?.open()}
      />
      <HelpConnectApiDialog ref={helpConnectApiRef} disabled={isTrialExpired} />

      <div className="flex items-center gap-1 sm:gap-1.5">
      {/* Notifications */}
      <DropdownMenu onOpenChange={(open) => open && void loadExpenseNotifications()}>
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="inline-flex">
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={t("header.notifications")}
                  className="relative shrink-0 h-9 w-8 px-0 sm:h-10 sm:w-9"
                >
                  <Bell className="w-4 h-4 sm:w-5 sm:h-5" aria-hidden />
                  {expenseNotificationsCount > 0 && (
                    <Badge className="absolute -right-1 -top-1 h-4 min-w-4 px-1 text-[10px] leading-none">
                      {expenseNotificationsCount > 99 ? "99+" : expenseNotificationsCount}
                    </Badge>
                  )}
                </Button>
              </DropdownMenuTrigger>
            </span>
          </TooltipTrigger>
          <TooltipContent side="bottom">
            {t("header.notifications")}
          </TooltipContent>
        </Tooltip>
        <DropdownMenuContent align="end" className="w-80 bg-card border-border">
          <DropdownMenuLabel className="text-base font-semibold">{t("header.notifications")}</DropdownMenuLabel>
          <DropdownMenuSeparator />
          {expenseNotificationsLoading ? (
            <div className="px-3 py-4 text-sm text-muted-foreground">{t("expense.loading")}</div>
          ) : expenseNotifications.length === 0 ? (
            <div className="px-3 py-4 text-sm text-muted-foreground">{t("header.noNotifications")}</div>
          ) : (
            <div className="max-h-80 overflow-y-auto">
              {expenseNotifications.map((notification) => (
                <div key={notification.id} className="flex gap-2 border-b border-border/50 px-3 py-2 last:border-0">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-foreground">
                      {getExpenseNotificationService(notification, language)}
                    </p>
                    <div className="mt-1 flex items-center justify-between gap-3 text-xs text-muted-foreground">
                      <span>{formatNotificationDate(notification.written_off_date)}</span>
                      <span className="font-semibold text-foreground">
                        {formatCurrency(notification.amount_sum, language === "uz" ? "so'm" : "сум")}
                      </span>
                    </div>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    aria-label={t("header.deleteNotification")}
                    title={t("header.deleteNotification")}
                    className="h-7 w-7 shrink-0 text-muted-foreground hover:text-destructive"
                    onClick={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      dismissExpenseNotification(notification.id);
                    }}
                    onPointerDown={(event) => event.stopPropagation()}
                  >
                    <Trash2 className="h-4 w-4" aria-hidden />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Help — заметная кнопка, подпись на sm+, подсказка при наведении */}
      <DropdownMenu>
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="inline-flex">
              <DropdownMenuTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  aria-label={t("header.help")}
                  className="gap-2 border-primary/25 bg-primary/5 hover:bg-primary/10 text-foreground shrink-0 h-9 sm:h-10 px-2.5 sm:px-3"
                >
                  <HelpCircle className="w-4 h-4 sm:w-5 sm:h-5 text-primary shrink-0" aria-hidden />
                  <span className="hidden sm:inline text-sm font-medium">{t("header.help")}</span>
                </Button>
              </DropdownMenuTrigger>
            </span>
          </TooltipTrigger>
          <TooltipContent side="bottom" align="end" className="max-w-xs text-center">
            {t("header.helpTooltip")}
          </TooltipContent>
        </Tooltip>
        <DropdownMenuContent align="end" className="w-64 sm:w-72 bg-card border-border">
          <DropdownMenuLabel className="text-base font-semibold">{t("header.help")}</DropdownMenuLabel>
          <DropdownMenuItem
            className="cursor-pointer"
            disabled={isTrialExpired}
            onSelect={() => {
              helpConnectApiRef.current?.open();
            }}
          >
            <KeyRound className="w-4 h-4 mr-2" />
            {t("header.helpConnectApi")}
          </DropdownMenuItem>
          <DropdownMenuItem className="cursor-pointer" asChild>
            <Link to="/training">
              <PlayCircle className="w-4 h-4 mr-2" />
              {t("header.videoTutorials")}
            </Link>
          </DropdownMenuItem>
          <DropdownMenuItem className="cursor-pointer" asChild>
            <Link to="/support?tab=contact">
              <MessageCircle className="w-4 h-4 mr-2" />
              {t("header.support")}
            </Link>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Language */}
      <DropdownMenu>
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="inline-flex">
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={t("header.language")}
                  className="shrink-0 h-9 w-8 px-0 sm:h-10 sm:w-9"
                >
                  <Globe className="w-4 h-4 sm:w-5 sm:h-5" aria-hidden />
                </Button>
              </DropdownMenuTrigger>
            </span>
          </TooltipTrigger>
          <TooltipContent side="bottom">{t("header.language")}</TooltipContent>
        </Tooltip>
        <DropdownMenuContent align="end" className="w-40 bg-card border-border">
          {headerLanguages.map(({ code, label }) => (
            <DropdownMenuItem
              key={code}
              className="cursor-pointer"
              onClick={() => setLanguage(code)}
            >
              <span className={language === code ? "font-semibold text-primary" : undefined}>{label}</span>
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* User Profile */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="gap-2 px-3">
            <User className="w-5 h-5" />
            <div className="flex flex-col items-start text-left">
              <span className="text-sm font-medium">{displayName}</span>
              <span className="text-xs text-muted-foreground">
                {user?.is_admin ? (
                  <span>{language === "uz" ? "Administrator" : "Администратор"}</span>
                ) : (
                  <>
                    <span>до: </span>
                    <span className={dateIsSoon ? "text-red-600 font-medium" : ""}>
                      {validUntilLabel ?? "—"}
                    </span>
                  </>
                )}
              </span>
            </div>
            <ChevronDown className="w-4 h-4 ml-1" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56 bg-card border-border">
          <DropdownMenuLabel>{t('header.myAccount')}</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem className="cursor-pointer" onClick={() => setProfileOpen(true)}>
            <User className="w-4 h-4 mr-2" />
            {t('header.profile')}
          </DropdownMenuItem>
          {user?.is_admin && (
            <DropdownMenuItem className="cursor-pointer" asChild>
              <Link to="/admin">
                <ShieldCheck className="w-4 h-4 mr-2" />
                {t('header.adminPanel')}
              </Link>
            </DropdownMenuItem>
          )}
          <DropdownMenuItem
            className="cursor-pointer text-primary"
            onClick={() => {
              setExtendVariant("extend");
              setExtendTariffOpen(true);
            }}
          >
            <CreditCard className="w-4 h-4 mr-2" />
            {t('header.extendTariff')}
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem className="cursor-pointer text-destructive" onClick={handleSignOut}>
            <LogOut className="w-4 h-4 mr-2" />
            {t('header.logout')}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      </div>

      {/* Тариф — полное окно с 4 планами и «Попробуй бесплатно» */}
      <PricingDialog open={tariffOpen} onOpenChange={setTariffOpen} variant="tariff" />
      {/* Продлить тариф — упрощённое окно «Тариф закончился» */}
      <PricingDialog open={extendTariffOpen} onOpenChange={setExtendTariffOpen} variant={extendVariant} />

      {/* Profile Dialog */}
      <ProfileDialog open={profileOpen} onOpenChange={setProfileOpen} />
    </div>
  );
}
