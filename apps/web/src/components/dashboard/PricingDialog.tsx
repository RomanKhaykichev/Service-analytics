import { Gift } from "lucide-react";
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

  if (variant === "extend" || variant === "expired") {
    return (
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
                <h3 className="font-semibold text-foreground text-sm mb-3">
                  {t(plan.titleKey)}
                </h3>
                <div className="text-2xl font-bold text-primary mb-0.5">{plan.price}</div>
                <span className="text-sm text-muted-foreground mb-4">{t("pricing.sum")}</span>
                <ul className="space-y-1 text-sm text-muted-foreground mb-4 flex-1">
                  {plan.featureKeys.map((key) => (
                    <li key={key}>– {t(key)}</li>
                  ))}
                </ul>
                <Button className="w-full bg-primary hover:bg-primary/90 text-primary-foreground">
                  {t("pricing.select")}
                </Button>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
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
