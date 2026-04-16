import { Gift } from "lucide-react";
import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useLanguage } from "@/contexts/LanguageContext";

interface PricingDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** "tariff" — полное окно тарифов (Тариф в меню); "extend" — упрощённое (Продлить тариф); "expired" — то же окно с заголовком «Тариф закончился» */
  variant?: "tariff" | "extend" | "expired";
}

const extendPlans = [
  {
    titleKey: "pricing.subscription1Month" as const,
    price: "269 000",
    featureKeys: ["pricing.upTo5Stores", "pricing.dataAnyPeriod"] as const,
    highlighted: false,
  },
  {
    titleKey: "pricing.subscription1Month" as const,
    price: "399 000",
    featureKeys: ["pricing.upTo10Stores", "pricing.dataAnyPeriod"] as const,
    highlighted: true,
  },
];

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

  if (variant === "extend" || variant === "expired") {
    return (
      <>
        <Dialog open={open} onOpenChange={onOpenChange}>
          <DialogContent className="sm:max-w-xl bg-card" hideCloseButton>
            <DialogHeader>
              <DialogTitle className="text-xl font-bold text-center">
                {variant === "expired" ? t("pricing.expiredTitle") : t("pricing.extendTitle")}
              </DialogTitle>
            </DialogHeader>
            <div className="grid grid-cols-2 gap-4 mt-4">
              {extendPlans.map((plan) => (
                <div
                  key={plan.price}
                  className={`flex flex-col p-4 rounded-xl border-2 transition-all ${
                    plan.highlighted ? "border-primary bg-primary/5" : "border-border bg-muted/30"
                  }`}
                >
                  <div className="mb-3 flex items-center justify-between gap-2">
                    <h3 className="font-semibold text-foreground text-sm">
                      {t(plan.titleKey)}
                    </h3>
                    {plan.price === "269 000" ? (
                      <span className="inline-flex items-center rounded-full border border-sky-300/60 bg-sky-50 px-3 py-1 text-sky-700 font-semibold text-xs">
                        Month 5
                      </span>
                    ) : (
                      <span className="inline-flex items-center rounded-full border border-violet-300/60 bg-violet-50 px-3 py-1 text-violet-700 font-semibold text-xs shadow-sm">
                        Month 10
                      </span>
                    )}
                  </div>
                  <div className="text-2xl font-bold text-primary mb-0.5">{plan.price}</div>
                  <span className="text-sm text-muted-foreground mb-4">{t("pricing.sum")}</span>
                  <ul className="space-y-1 text-sm text-muted-foreground mb-4 flex-1">
                    {plan.featureKeys.map((key) => (
                      <li key={key}>– {t(key)}</li>
                    ))}
                  </ul>
                  <Button
                    className="w-full bg-primary hover:bg-primary/90 text-primary-foreground"
                    onClick={openPaymentDialog}
                  >
                    {t("pricing.select")}
                  </Button>
                </div>
              ))}
            </div>
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
                        <span className="inline-flex items-center rounded-full border border-sky-300/60 bg-sky-50 px-3 py-1 text-sky-700 font-semibold">
                          {t("pricing.month5Price")}
                        </span>
                        <span className="inline-flex items-center rounded-full border border-violet-300/60 bg-violet-50 px-3 py-1 text-violet-700 font-semibold shadow-sm">
                          {t("pricing.month10Price")}
                        </span>
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
                href="https://t.me/PROFI_BOARD"
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
