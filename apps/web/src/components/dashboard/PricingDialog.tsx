import { Check, Gift } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface PricingDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const pricingPlans = [
  {
    duration: "1 месяц",
    price: "269 000",
    savings: null,
    popular: false,
  },
  {
    duration: "3 месяца",
    price: "750 000",
    savings: "10%",
    popular: false,
  },
  {
    duration: "6 месяцев",
    price: "1 380 000",
    savings: "18%",
    popular: true,
  },
  {
    duration: "1 год",
    price: "2 400 000",
    savings: "25%",
    popular: false,
  },
];

export function PricingDialog({ open, onOpenChange }: PricingDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl bg-card">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold text-center">
            Выберите тариф
          </DialogTitle>
        </DialogHeader>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
          {pricingPlans.map((plan) => (
            <div
              key={plan.duration}
              className={`relative flex flex-col p-4 rounded-xl border-2 transition-all hover:border-primary cursor-pointer ${
                plan.popular
                  ? "border-primary bg-primary/5"
                  : "border-border bg-muted/30"
              }`}
            >
              {plan.popular && (
                <Badge className="absolute -top-2 left-1/2 -translate-x-1/2 bg-primary text-primary-foreground text-xs">
                  Популярный
                </Badge>
              )}
              
              <div className="text-center">
                <h3 className="font-semibold text-foreground mb-2">
                  {plan.duration}
                </h3>
                <div className="text-lg font-bold text-primary mb-1">
                  {plan.price}
                </div>
                <span className="text-xs text-muted-foreground">сум</span>
              </div>

              {plan.savings && (
                <Badge 
                  variant="secondary" 
                  className="mt-3 mx-auto bg-green-500/10 text-green-600 border-green-500/20"
                >
                  Экономия {plan.savings}
                </Badge>
              )}

              <Button
                className="mt-4 w-full"
                variant={plan.popular ? "default" : "outline"}
                size="sm"
              >
                Выбрать
              </Button>
            </div>
          ))}
        </div>

        {/* Free Trial */}
        <div className="mt-6 p-4 rounded-xl border-2 border-dashed border-primary/50 bg-primary/5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center">
                <Gift className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h3 className="font-semibold text-foreground">
                  Попробуй бесплатно
                </h3>
                <p className="text-sm text-muted-foreground">
                  10 дней полного доступа без оплаты
                </p>
              </div>
            </div>
            <Button variant="default" className="bg-primary hover:bg-primary/90">
              Начать бесплатно
            </Button>
          </div>
        </div>

        <p className="text-xs text-muted-foreground text-center mt-4">
          Отмена подписки доступна в любой момент
        </p>
      </DialogContent>
    </Dialog>
  );
}
