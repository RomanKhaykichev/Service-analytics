import { useState, useEffect, useRef, useCallback } from "react";
import { Bell, HelpCircle, User, ChevronDown, LogOut, CreditCard, Globe, PlayCircle, MessageCircle, ShieldCheck, KeyRound, Trash2, CircleDollarSign } from "lucide-react";
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

const DISMISSED_NOTIFICATIONS_PREFIX = "dismissed_header_notifications";
const DISMISSED_EXPENSE_NOTIFICATIONS_PREFIX = "dismissed_expense_notifications";

function getUserDisplayName(user: { full_name?: string; user_metadata?: { full_name?: string }; email?: string } | null): string {
  if (!user) return "Пользователь";
  if (user.full_name) return user.full_name;
  if (user.user_metadata?.full_name) return user.user_metadata.full_name;
  if (user.email) return user.email;
  return "Пользователь";
}

export interface RatingNotificationProduct {
  product_id: string;
  product_name: string;
  rating: number | null;
  feedback_quantity: number | null;
}

interface HeaderActionsProps {
  apiConnectRef?: React.RefObject<UzumApiConnectDialogHandle | null>;
  onOpenRatingProduct?: (product: RatingNotificationProduct) => void;
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

interface RatingNotification {
  id: string;
  product_id: string;
  product_name: string;
  rating: number | null;
  feedback_quantity: number | null;
  updated_at?: string | null;
}

interface RatingNotificationsResponse {
  items: RatingNotification[];
  count: number;
}

type HeaderNotification =
  | { kind: "expense"; data: ExpenseNotification }
  | { kind: "rating"; data: RatingNotification };

function getNotificationSortTime(notification: HeaderNotification): number {
  if (notification.kind === "expense") {
    const date = notification.data.written_off_date;
    if (!date) return 0;
    const parsed = new Date(`${date}T12:00:00`);
    return Number.isNaN(parsed.getTime()) ? 0 : parsed.getTime();
  }
  const updatedAt = notification.data.updated_at;
  if (!updatedAt) return 0;
  const parsed = new Date(updatedAt);
  return Number.isNaN(parsed.getTime()) ? 0 : parsed.getTime();
}

function sortNotificationsNewestFirst(items: HeaderNotification[]): HeaderNotification[] {
  return [...items].sort((a, b) => {
    const timeDiff = getNotificationSortTime(b) - getNotificationSortTime(a);
    if (timeDiff !== 0) return timeDiff;
    if (a.kind === "expense" && b.kind === "expense") {
      return (b.data.amount_sum ?? 0) - (a.data.amount_sum ?? 0);
    }
    if (a.kind === "rating" && b.kind === "rating") {
      return (a.data.rating ?? 0) - (b.data.rating ?? 0);
    }
    return 0;
  });
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

function getDismissedNotificationsKey(userId: string): string {
  return `${DISMISSED_NOTIFICATIONS_PREFIX}:${userId}`;
}

function readDismissedNotificationIds(userId: string): Set<string> {
  try {
    const raw = localStorage.getItem(getDismissedNotificationsKey(userId));
    if (raw) {
      const parsed = JSON.parse(raw);
      return new Set(Array.isArray(parsed) ? parsed.filter((id): id is string => typeof id === "string") : []);
    }
    // Migrate legacy expense-only dismissals.
    const legacyRaw = localStorage.getItem(getDismissedExpenseNotificationsKey(userId));
    if (!legacyRaw) return new Set();
    const legacyParsed = JSON.parse(legacyRaw);
    const legacyIds = new Set(Array.isArray(legacyParsed) ? legacyParsed.filter((id): id is string => typeof id === "string") : []);
    if (legacyIds.size > 0) {
      writeDismissedNotificationIds(userId, legacyIds);
    }
    return legacyIds;
  } catch {
    return new Set();
  }
}

function writeDismissedNotificationIds(userId: string, ids: Set<string>): void {
  try {
    localStorage.setItem(getDismissedNotificationsKey(userId), JSON.stringify([...ids]));
  } catch {
    // If storage is unavailable, keep the UI-only removal for the current state.
  }
}

function getDismissedExpenseNotificationsKey(userId: string): string {
  return `${DISMISSED_EXPENSE_NOTIFICATIONS_PREFIX}:${userId}`;
}

function formatProductRatingNotification(
  rating: number | null | undefined,
  feedbackQuantity: number | null | undefined,
  ratingPrefix: string,
): string | null {
  if (rating == null && feedbackQuantity == null) return null;
  const ratingValue = rating != null ? rating.toFixed(1) : "—";
  const count = feedbackQuantity ?? 0;
  return `${ratingPrefix} ${ratingValue} (${count}) ⭐️`;
}

export function HeaderActions({
  apiConnectRef: apiConnectRefProp,
  onOpenRatingProduct,
}: HeaderActionsProps = {}) {
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
  const [notifications, setNotifications] = useState<HeaderNotification[]>([]);
  const [notificationsCount, setNotificationsCount] = useState(0);
  const [notificationsLoading, setNotificationsLoading] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
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

  const loadNotifications = useCallback(async () => {
    if (!user?.id) {
      setNotifications([]);
      setNotificationsCount(0);
      return;
    }

    setNotificationsLoading(true);
    try {
      const [expensesResult, ratingsResult] = await Promise.allSettled([
        apiGet<ExpenseNotificationsResponse>("/api/notifications/expenses"),
        apiGet<RatingNotificationsResponse>("/api/notifications/ratings"),
      ]);
      const dismissedIds = readDismissedNotificationIds(user.id);

      const expensesData =
        expensesResult.status === "fulfilled" ? expensesResult.value : { items: [], count: 0 };
      const ratingsData =
        ratingsResult.status === "fulfilled" ? ratingsResult.value : { items: [], count: 0 };

      const expenseItems: HeaderNotification[] = (expensesData.items ?? [])
        .filter((item) => !dismissedIds.has(item.id))
        .map((item) => ({ kind: "expense", data: item }));

      const ratingItems: HeaderNotification[] = (ratingsData.items ?? [])
        .filter((item) => !dismissedIds.has(item.id))
        .map((item) => ({ kind: "rating", data: item }));

      const merged = sortNotificationsNewestFirst([...expenseItems, ...ratingItems]);
      const totalCount = (expensesData.count ?? 0) + (ratingsData.count ?? 0);

      setNotifications(merged);
      setNotificationsCount(Math.max(0, totalCount - dismissedIds.size));
    } catch {
      setNotifications([]);
      setNotificationsCount(0);
    } finally {
      setNotificationsLoading(false);
    }
  }, [user?.id]);

  // Подгружаем счётчик уведомлений с задержкой, чтобы не мешать первому входу в сервис.
  useEffect(() => {
    if (!user?.id) return;
    const timer = window.setTimeout(() => {
      void loadNotifications();
    }, 1500);
    return () => window.clearTimeout(timer);
  }, [user?.id, loadNotifications]);

  const dismissNotification = useCallback((id: string) => {
    if (!user?.id) return;

    const dismissedIds = readDismissedNotificationIds(user.id);
    dismissedIds.add(id);
    writeDismissedNotificationIds(user.id, dismissedIds);
    setNotifications((items) => items.filter((item) => item.data.id !== id));
    setNotificationsCount((count) => Math.max(0, count - 1));
  }, [user?.id]);

  const dismissAllNotifications = useCallback(async () => {
    if (!user?.id) return;

    const [expensesResult, ratingsResult] = await Promise.allSettled([
      apiGet<ExpenseNotificationsResponse>("/api/notifications/expenses"),
      apiGet<RatingNotificationsResponse>("/api/notifications/ratings"),
    ]);

    const dismissedIds = readDismissedNotificationIds(user.id);

    if (expensesResult.status === "fulfilled") {
      for (const item of expensesResult.value.items ?? []) {
        dismissedIds.add(item.id);
      }
    }
    if (ratingsResult.status === "fulfilled") {
      for (const item of ratingsResult.value.items ?? []) {
        dismissedIds.add(item.id);
      }
    }

    writeDismissedNotificationIds(user.id, dismissedIds);
    setNotifications([]);
    setNotificationsCount(0);
  }, [user?.id]);

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
      <DropdownMenu
        open={notificationsOpen}
        onOpenChange={(open) => {
          setNotificationsOpen(open);
          if (open) void loadNotifications();
        }}
      >
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
                  {notificationsCount > 0 && (
                    <Badge className="absolute -right-1 -top-1 h-4 min-w-4 px-1 text-[10px] leading-none">
                      {notificationsCount > 99 ? "99+" : notificationsCount}
                    </Badge>
                  )}
                </Button>
              </DropdownMenuTrigger>
            </span>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="max-w-xs text-center">
            {t("header.notificationsTooltip")}
          </TooltipContent>
        </Tooltip>
        <DropdownMenuContent align="end" className="w-80 bg-card border-border">
          <div className="flex items-center justify-between gap-2 px-2 py-1.5">
            <DropdownMenuLabel className="p-0 text-base font-semibold">
              {t("header.notifications")}
            </DropdownMenuLabel>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-auto shrink-0 px-2 py-1 text-xs font-normal text-muted-foreground hover:text-foreground"
              disabled={notificationsLoading || (notifications.length === 0 && notificationsCount === 0)}
              aria-label={t("header.deleteAllNotifications")}
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                void dismissAllNotifications();
              }}
              onPointerDown={(event) => event.stopPropagation()}
            >
              {t("header.deleteAllNotifications")}
            </Button>
          </div>
          <DropdownMenuSeparator />
          {notificationsLoading ? (
            <div className="px-3 py-4 text-sm text-muted-foreground">{t("expense.loading")}</div>
          ) : notifications.length === 0 ? (
            <div className="px-3 py-4 text-sm text-muted-foreground">{t("header.noNotifications")}</div>
          ) : (
            <div className="max-h-80 overflow-y-auto">
              {notifications.map((notification) => {
                if (notification.kind === "expense") {
                  const item = notification.data;
                  return (
                    <div key={item.id} className="flex gap-2 border-b border-border/50 px-3 py-2 last:border-0">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-foreground">
                          {getExpenseNotificationService(item, language)}
                        </p>
                        <div className="mt-1 flex items-center justify-between gap-3 text-xs text-muted-foreground">
                          <span>{formatNotificationDate(item.written_off_date)}</span>
                          <span className="font-semibold text-foreground">
                            {formatCurrency(item.amount_sum, language === "uz" ? "so'm" : "сум")}
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
                          dismissNotification(item.id);
                        }}
                        onPointerDown={(event) => event.stopPropagation()}
                      >
                        <Trash2 className="h-4 w-4" aria-hidden />
                      </Button>
                    </div>
                  );
                }

                const item = notification.data;
                const ratingLine = formatProductRatingNotification(
                  item.rating,
                  item.feedback_quantity,
                  t("product.ratingPrefix"),
                );
                return (
                  <div key={item.id} className="flex gap-2 border-b border-border/50 px-3 py-2 last:border-0">
                    <button
                      type="button"
                      className="min-w-0 flex-1 rounded-md text-left transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-default disabled:hover:bg-transparent"
                      disabled={!onOpenRatingProduct || !item.product_id}
                      aria-label={t("notification.openProductCard")}
                      onClick={() => {
                        if (!onOpenRatingProduct || !item.product_id) return;
                        onOpenRatingProduct({
                          product_id: item.product_id,
                          product_name: item.product_name,
                          rating: item.rating,
                          feedback_quantity: item.feedback_quantity,
                        });
                        setNotificationsOpen(false);
                      }}
                    >
                      <p className="text-sm font-medium text-foreground">
                        {t("notification.lowRating")}
                      </p>
                      {item.product_name ? (
                        <p className="mt-1 text-xs text-muted-foreground truncate">{item.product_name}</p>
                      ) : null}
                      {ratingLine ? (
                        <p className="mt-1 text-xs text-muted-foreground">{ratingLine}</p>
                      ) : null}
                    </button>
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
                        dismissNotification(item.id);
                      }}
                      onPointerDown={(event) => event.stopPropagation()}
                    >
                      <Trash2 className="h-4 w-4" aria-hidden />
                    </Button>
                  </div>
                );
              })}
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
          <DropdownMenuItem className="cursor-pointer" asChild>
            <Link to="/cogs">
              <CircleDollarSign className="w-4 h-4 mr-2" />
              {t("header.enterCogs")}
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
