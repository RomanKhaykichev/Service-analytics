import { Check, Gift, Star } from "lucide-react";
import { useState, useEffect } from "react";
import { apiPost } from "@/lib/api";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useLanguage } from "@/contexts/LanguageContext";
import { cn } from "@/lib/utils";
import { getMonthTariffPillClass } from "@/lib/tariffPill";

interface PricingDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** "tariff" — полное окно тарифов (Тариф в меню); "extend" — упрощённое (Продлить тариф); "expired" — то же окно с заголовком «Тариф закончился» */
  variant?: "tariff" | "extend" | "expired";
}

const extendPlans = [
  {
    id: "month5",
    nameKey: "pricing.planStandard" as const,
    monthLabel: "Month 5",
    originalPrice: "269 000",
    price: "190 000",
    discount: "-30%",
    promoLabelKey: "pricing.launchPrice" as const,
    featureKeys: ["pricing.upTo5Stores", "pricing.dataAnyPeriod", "pricing.allFeatures"] as const,
    highlighted: true,
  },
  {
    id: "month10",
    nameKey: "pricing.planBusiness" as const,
    monthLabel: "Month 10",
    originalPrice: "399 000",
    price: "280 000",
    discount: "-30%",
    promoLabelKey: "pricing.forGrowingBusiness" as const,
    featureKeys: ["pricing.upTo10Stores", "pricing.dataAnyPeriod", "pricing.allFeatures"] as const,
    highlighted: false,
  },
] as const;

const EXTEND_NAVY = "#0f172a";
const EXTEND_ACCENT = "#7c3aed";
const EXTEND_ACCENT_SOFT = "#ede9fe";
const EXTEND_HIGHLIGHT = "#7c3aed";

function ExtendPlanPrice({
  originalPrice,
  price,
}: {
  originalPrice: string;
  price: string;
}) {
  return (
    <span className="inline-flex flex-wrap items-baseline gap-1.5">
      <span className="line-through opacity-70">{originalPrice}</span>
      <span>{price}</span>
    </span>
  );
}

function FeatureCheckIcon({ plain = false }: { plain?: boolean }) {
  if (plain) {
    return (
      <Check
        className="mt-0.5 h-3.5 w-3.5 shrink-0"
        style={{ color: EXTEND_ACCENT }}
        strokeWidth={3}
        aria-hidden
      />
    );
  }

  return (
    <span
      className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full"
      style={{ backgroundColor: EXTEND_ACCENT }}
      aria-hidden
    >
      <Check className="h-2.5 w-2.5 text-white" strokeWidth={3} />
    </span>
  );
}

function PromoGiftIllustration() {
  const confetti = [
    "top-0 left-4 h-1.5 w-1.5 bg-violet-400",
    "top-2 right-1 h-1 w-1 bg-amber-400",
    "bottom-2 left-1 h-1 w-1 bg-orange-400",
    "bottom-4 right-3 h-1.5 w-1.5 bg-violet-300",
    "top-6 left-2 h-1 w-1 bg-yellow-400",
  ];

  return (
    <div className="relative mx-auto h-[74px] w-[74px] shrink-0 sm:mx-0" aria-hidden>
      {confetti.map((className) => (
        <span key={className} className={cn("absolute rounded-full", className)} />
      ))}
      <div className="absolute inset-x-3 bottom-2 top-5 rounded-xl bg-gradient-to-br from-[#9b6bff] to-[#6d28d9] shadow-[0_10px_20px_rgba(109,40,217,0.28)]">
        <div className="absolute left-1/2 top-0 h-full w-3 -translate-x-1/2 bg-[#fbbf24]" />
        <div className="absolute left-0 top-1/2 h-3 w-full -translate-y-1/2 bg-[#fbbf24]" />
      </div>
      <div className="absolute left-1/2 top-3 h-6 w-9 -translate-x-1/2 rounded-t-full bg-[#fcd34d]" />
      <div className="absolute left-1/2 top-1 h-3.5 w-3.5 -translate-x-1/2 rounded-full bg-[#f59e0b]" />
    </div>
  );
}

function PromoGiftImage() {
  const [useFallback, setUseFallback] = useState(false);

  if (useFallback) {
    return <PromoGiftIllustration />;
  }

  return (
    <img
      src="/images/pricing-promo-gift.png"
      alt=""
      aria-hidden
      className="mx-auto h-[80px] w-[86px] shrink-0 object-contain sm:mx-0"
      onError={() => setUseFallback(true)}
    />
  );
}

function PromoParticipationPanel() {
  const { t } = useLanguage();

  return (
    <div className="flex w-full shrink-0 flex-col gap-2.5 sm:max-w-[220px]">
      <div className="-ml-1 flex items-center gap-1">
        <img
          src="/images/pricing-participants-icon.png"
          alt=""
          aria-hidden
          className="h-5 w-5 shrink-0 object-contain"
        />
        <p className="text-[11px] font-bold leading-tight text-[#5d3eb3]">
          {t("pricing.promoParticipationTitle")}
        </p>
      </div>
      <ul className="flex flex-col gap-2.5">
        <li className="flex items-start gap-2">
          <FeatureCheckIcon plain />
          <div className="min-w-0">
            <span className="block text-[10px] font-bold leading-snug text-[#1a1a1a]">
              {t("pricing.promoTelegram")}
            </span>
            <span className="mt-0.5 block text-[9px] font-normal leading-snug text-[#666666]">
              {t("pricing.promoTelegramHint")}
            </span>
          </div>
        </li>
        <li className="flex items-start gap-2">
          <FeatureCheckIcon plain />
          <div className="min-w-0">
            <span className="block text-[10px] font-bold leading-snug text-[#1a1a1a]">
              {t("pricing.promoFeedback")}
            </span>
            <span className="mt-0.5 block text-[9px] font-normal leading-snug text-[#666666]">
              {t("pricing.promoFeedbackHint")}
            </span>
          </div>
        </li>
      </ul>
    </div>
  );
}

function ExtendPromoBanner() {
  const { t } = useLanguage();

  return (
    <div className="mt-4 rounded-2xl border border-[#ffd7a0] bg-[#fff9f0] px-4 py-2.5">
      <div className="flex flex-col items-center gap-2.5 sm:flex-row sm:items-center sm:gap-3">
        <PromoGiftImage />

        <div className="min-w-0 flex-1 text-center sm:text-left">
          <span className="mb-1 inline-block rounded-full bg-[#f2994a] px-2.5 py-0.5 text-[9px] font-bold uppercase tracking-wide text-white">
            {t("pricing.limitedOffer")}
          </span>
          <h4 className="text-[15px] font-bold leading-tight">
            <span className="text-[#2d0c8e]">{t("pricing.onePlusOnePrefix")}</span>
            <span className="text-black">{t("pricing.onePlusOneHighlight")}</span>
          </h4>
          <p className="mt-0.5 text-[11px] leading-snug text-[#4f4f4f]">
            {t("pricing.onePlusOneDescPrefix")}
            <span className="font-bold" style={{ color: EXTEND_HIGHLIGHT }}>
              {t("pricing.onePlusOneDescHighlight")}
            </span>
          </p>
        </div>

        <PromoParticipationPanel />
      </div>
    </div>
  );
}

const pricingPlans = [
  { durationKey: "pricing.month1" as const, price: "269 000", savings: null, popular: false },
  { durationKey: "pricing.month3" as const, price: "750 000", savings: "10%", popular: false },
  { durationKey: "pricing.month6" as const, price: "1 380 000", savings: "18%", popular: true },
  { durationKey: "pricing.year1" as const, price: "2 400 000", savings: "25%", popular: false },
];

export function PricingDialog({ open, onOpenChange, variant = "tariff" }: PricingDialogProps) {
  const { t } = useLanguage();
  const [isPaymentDialogOpen, setIsPaymentDialogOpen] = useState(false);
  const [isTelegramDialogOpen, setIsTelegramDialogOpen] = useState(false);
  const openPaymentDialog = () => {
    onOpenChange(false);
    setIsPaymentDialogOpen(true);
  };

  useEffect(() => {
    if (isPaymentDialogOpen) {
      apiPost("/api/track/tariff-payment-open", {}).catch(() => {});
    }
  }, [isPaymentDialogOpen]);

  if (variant === "extend" || variant === "expired") {
    return (
      <>
        <Dialog open={open} onOpenChange={onOpenChange}>
          <DialogContent
            className="gap-0 overflow-y-auto rounded-2xl border-0 bg-white p-4 shadow-xl sm:max-w-[620px] sm:p-5"
            hideCloseButton
            overlayClassName="bg-black/50"
          >
            <DialogHeader className="flex flex-col items-center space-y-2 text-center">
              <DialogTitle
                className="mx-auto max-w-md text-center text-base font-bold leading-snug sm:text-[17px]"
                style={{ color: EXTEND_NAVY }}
              >
                {variant === "expired" ? t("pricing.expiredHeroTitle") : t("pricing.extendHeroTitle")}
              </DialogTitle>
              <p className="mx-auto max-w-md text-center text-xs leading-snug text-slate-500">
                {t("pricing.extendHeroSubtitlePrefix")}
                <span className="font-bold" style={{ color: EXTEND_HIGHLIGHT }}>
                  {t("pricing.extendHeroSubtitleHighlight")}
                </span>
                .
              </p>
            </DialogHeader>

            <div className="mt-5 grid grid-cols-2 items-stretch gap-3">
              {extendPlans.map((plan) => (
                <div
                  key={plan.id}
                  className={cn(
                    "relative flex h-full flex-col rounded-2xl border-2 bg-white px-3.5 pb-3.5 pt-5 shadow-sm",
                    plan.highlighted
                      ? "border-[#7c3aed] shadow-[0_4px_16px_rgba(124,58,237,0.14)]"
                      : "border-slate-200",
                  )}
                >
                  {plan.highlighted && (
                    <Badge
                      className="absolute -top-3 left-1/2 flex -translate-x-1/2 items-center gap-1 rounded-lg border-0 px-3 py-1 text-[11px] font-semibold text-white shadow-sm"
                      style={{ backgroundColor: EXTEND_ACCENT }}
                    >
                      <Star className="h-3.5 w-3.5 fill-[#fbbf24] text-[#fbbf24]" aria-hidden />
                      {t("pricing.popular")}
                    </Badge>
                  )}

                  <div className="mb-2.5 flex items-start justify-between gap-2">
                    <h3 className="text-[15px] font-bold leading-tight" style={{ color: EXTEND_ACCENT }}>
                      {t(plan.nameKey)}
                    </h3>
                    <span
                      className={cn(
                        "inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-[10px] font-semibold",
                        getMonthTariffPillClass(plan.id),
                      )}
                    >
                      {plan.monthLabel}
                    </span>
                  </div>

                  <p className="text-xs text-slate-400 line-through">{plan.originalPrice}</p>
                  <div className="mt-0.5 flex flex-wrap items-baseline gap-x-1">
                    <span className="text-[26px] font-bold leading-none" style={{ color: EXTEND_ACCENT }}>
                      {plan.price}
                    </span>
                    <span className="text-[11px] font-medium" style={{ color: EXTEND_ACCENT }}>
                      {t("pricing.perMonth")}
                    </span>
                  </div>
                  <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                    <span
                      className="inline-flex rounded-lg px-2 py-0.5 text-[10px] font-semibold"
                      style={{ backgroundColor: EXTEND_ACCENT_SOFT, color: EXTEND_ACCENT }}
                    >
                      {plan.discount}
                    </span>
                    <span
                      className="inline-flex rounded-lg px-2 py-0.5 text-[10px] font-medium"
                      style={{ backgroundColor: "#f3efff", color: "#6a49b1" }}
                    >
                      {t(plan.promoLabelKey)}
                    </span>
                  </div>

                  <ul className="mb-4 mt-3.5 flex-1 space-y-2.5 border-t border-slate-100 pt-3">
                    {plan.featureKeys.map((key) => (
                      <li key={key} className="flex items-start gap-2 text-[11px] leading-snug text-slate-800">
                        <FeatureCheckIcon />
                        <span>{t(key)}</span>
                      </li>
                    ))}
                  </ul>

                  <Button
                    className="mt-auto h-9 w-full rounded-lg text-xs font-semibold text-white hover:opacity-90"
                    style={{ backgroundColor: EXTEND_ACCENT }}
                    onClick={openPaymentDialog}
                  >
                    {t("pricing.selectTariff")}
                  </Button>
                </div>
              ))}
            </div>

            <ExtendPromoBanner />
          </DialogContent>
        </Dialog>

        <Dialog open={isPaymentDialogOpen} onOpenChange={setIsPaymentDialogOpen}>
          <DialogContent className="sm:max-w-4xl bg-card">
            <DialogHeader>
              <DialogTitle className="text-xl font-bold">
                {t("pricing.paymentTitle")}
              </DialogTitle>
            </DialogHeader>
            <div className="mt-4 grid gap-6 md:grid-cols-[300px_minmax(0,1fr)]">
              <div className="rounded-xl border-2 border-dashed border-border bg-muted/20 p-4 flex items-center justify-center min-h-[300px]">
                <img
                  src="/images/payment-qr.png"
                  alt={t("pricing.paymentTitle")}
                  className="w-full max-w-[260px] h-auto object-contain"
                  width={260}
                  height={260}
                  loading="lazy"
                />
              </div>
              <div className="space-y-4 text-sm text-foreground">
                <p className="text-foreground/90">
                  {t("pricing.paymentNoticeLine1")}
                  <br />
                  {t("pricing.paymentNoticeLine2")}
                </p>
                <div>
                  <p className="font-semibold">{t("pricing.howToPayTitle")}</p>
                  <ol className="mt-2 space-y-2 list-decimal pl-5 text-foreground/90">
                    <li>
                      <p>{t("pricing.stepOpenAppLine1")}</p>
                      <p>{t("pricing.stepOpenAppLine2")}</p>
                      <div className="mt-2 flex flex-wrap items-center gap-3">
                        <img
                          src="/images/payme-logo.png"
                          alt="Payme logo"
                          className="h-8 w-auto object-contain"
                          loading="lazy"
                        />
                        <img
                          src="/images/click-logo.png"
                          alt="Click logo"
                          className="h-8 w-auto object-contain"
                          loading="lazy"
                        />
                      </div>
                    </li>
                    <li>{t("pricing.stepScanQr")}</li>
                    <li>
                      {t("pricing.stepEnterAmount")}
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        {extendPlans.map((plan) => (
                          <span
                            key={plan.id}
                            className={cn(
                              "inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold",
                              getMonthTariffPillClass(plan.id),
                            )}
                          >
                            {plan.monthLabel} —{" "}
                            <ExtendPlanPrice originalPrice={plan.originalPrice} price={plan.price} />{" "}
                            {t("pricing.sum")}
                          </span>
                        ))}
                      </div>
                    </li>
                    <li>{t("pricing.stepScreenshot")}</li>
                    <li>
                      {t("pricing.stepSendTelegramLine1")}
                      {t("pricing.stepSendTelegramLine2")}
                    </li>
                  </ol>
                </div>
                <div className="rounded-lg border border-amber-300/50 bg-amber-50 px-3 py-2 text-amber-900">
                  <p className="font-semibold">{t("pricing.importantTitle")}</p>
                  <p className="mt-1">
                    {t("pricing.importantText")}
                  </p>
                </div>
                <div className="pt-1">
                  <Button onClick={() => setIsTelegramDialogOpen(true)}>
                    {t("pricing.goToTelegram")}
                  </Button>
                </div>
              </div>
            </div>
          </DialogContent>
        </Dialog>

        <Dialog open={isTelegramDialogOpen} onOpenChange={setIsTelegramDialogOpen}>
          <DialogContent className="sm:max-w-md bg-card" overlayClassName="bg-black/60">
            <DialogHeader>
              <DialogTitle className="text-xl font-bold">
                {t("pricing.telegramTitle")}
              </DialogTitle>
            </DialogHeader>
            <div className="mt-3 flex flex-col items-center gap-3">
              <a
                href="https://t.me/PROFiboard"
                target="_blank"
                rel="noopener noreferrer"
                className="block w-full max-w-[280px] rounded-xl overflow-hidden ring-1 ring-border/70 bg-card transition-opacity hover:opacity-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <img
                  src="/images/telegram-qr-receipt.png"
                  alt={t("support.telegramQrAlt")}
                  className="w-full h-auto object-contain"
                  width={280}
                  height={280}
                  loading="lazy"
                />
              </a>
            </div>
          </DialogContent>
        </Dialog>
      </>
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl bg-card">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold text-center">
            {t("pricing.chooseTariff")}
          </DialogTitle>
        </DialogHeader>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
          {pricingPlans.map((plan) => (
            <div
              key={plan.durationKey}
              className={`relative flex flex-col p-4 rounded-xl border-2 transition-all hover:border-primary cursor-pointer ${
                plan.popular ? "border-primary bg-primary/5" : "border-border bg-muted/30"
              }`}
            >
              {plan.popular && (
                <Badge className="absolute -top-2 left-1/2 -translate-x-1/2 bg-primary text-primary-foreground text-xs">
                  {t("pricing.popular")}
                </Badge>
              )}
              <div className="text-center">
                <h3 className="font-semibold text-foreground mb-2">{t(plan.durationKey)}</h3>
                <div className="text-lg font-bold text-primary mb-1">{plan.price}</div>
                <span className="text-xs text-muted-foreground">{t("pricing.sum")}</span>
              </div>
              {plan.savings && (
                <Badge
                  variant="secondary"
                  className="mt-3 mx-auto bg-green-500/10 text-green-600 border-green-500/20"
                >
                  {t("pricing.savings")} {plan.savings}
                </Badge>
              )}
              <Button
                className="mt-4 w-full"
                variant={plan.popular ? "default" : "outline"}
                size="sm"
              >
                {t("pricing.select")}
              </Button>
            </div>
          ))}
        </div>
        <div className="mt-6 p-4 rounded-xl border-2 border-dashed border-primary/50 bg-primary/5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center">
                <Gift className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h3 className="font-semibold text-foreground">{t("pricing.tryFree")}</h3>
                <p className="text-sm text-muted-foreground">
                  {t("pricing.tryFreeDesc")}
                </p>
              </div>
            </div>
            <Button variant="default" className="bg-primary hover:bg-primary/90">
              {t("pricing.startFree")}
            </Button>
          </div>
        </div>
        <p className="text-xs text-muted-foreground text-center mt-4">
          {t("pricing.cancelAnytime")}
        </p>
      </DialogContent>
    </Dialog>
  );
}
