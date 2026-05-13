import { useState, useEffect, useRef } from "react";
import { HelpCircle, User, ChevronDown, LogOut, CreditCard, Globe, PlayCircle, MessageCircle, ShieldCheck, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { ReportUploadDialog, type ReportUploadDialogHandle } from "./ReportUploadDialog";
import { PricingDialog } from "./PricingDialog";
import { ProfileDialog } from "./ProfileDialog";
import { LanguageDialog } from "./LanguageDialog";
import { useNavigate, Link } from "react-router-dom";
import { useLanguage } from "@/contexts/LanguageContext";
import { useAuth } from "@/hooks/useAuth";
import { useStorageShops } from "@/hooks/useStorageShops";
import { toast } from "sonner";

function getUserDisplayName(user: { full_name?: string; user_metadata?: { full_name?: string }; email?: string } | null): string {
  if (!user) return "Пользователь";
  if (user.full_name) return user.full_name;
  if (user.user_metadata?.full_name) return user.user_metadata.full_name;
  if (user.email) return user.email;
  return "Пользователь";
}

export function HeaderActions() {
  const { t, language } = useLanguage();
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
  const [languageOpen, setLanguageOpen] = useState(false);
  const reportUploadRef = useRef<ReportUploadDialogHandle>(null);
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
      reportUploadRef.current?.open("guided");
    });
  }, [user?.id, user?.is_admin, isTrialExpired, shopsLoading, shops.length]);

  return (
    <div className="flex items-center gap-6">
      {/* Report Upload */}
      <ReportUploadDialog
        ref={reportUploadRef}
        disabled={isTrialExpired}
        onOpenExtendTariff={() => {
          setExtendVariant("extend");
          setExtendTariffOpen(true);
        }}
      />

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
              reportUploadRef.current?.open("guided");
            }}
          >
            <Upload className="w-4 h-4 mr-2" />
            {t("header.helpUploadReports")}
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
          <DropdownMenuItem className="cursor-pointer" onClick={() => setLanguageOpen(true)}>
            <Globe className="w-4 h-4 mr-2" />
            {t('header.language')}
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem className="cursor-pointer text-destructive" onClick={handleSignOut}>
            <LogOut className="w-4 h-4 mr-2" />
            {t('header.logout')}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Тариф — полное окно с 4 планами и «Попробуй бесплатно» */}
      <PricingDialog open={tariffOpen} onOpenChange={setTariffOpen} variant="tariff" />
      {/* Продлить тариф — упрощённое окно «Тариф закончился» */}
      <PricingDialog open={extendTariffOpen} onOpenChange={setExtendTariffOpen} variant={extendVariant} />

      {/* Profile Dialog */}
      <ProfileDialog open={profileOpen} onOpenChange={setProfileOpen} />

      {/* Language Dialog */}
      <LanguageDialog open={languageOpen} onOpenChange={setLanguageOpen} />
    </div>
  );
}
