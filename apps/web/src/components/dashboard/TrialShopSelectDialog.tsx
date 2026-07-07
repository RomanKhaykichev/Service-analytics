import { useState } from "react";
import { Loader2, Store } from "lucide-react";import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { useLanguage } from "@/contexts/LanguageContext";
import type { TrialShopOption } from "@/hooks/useTrialShopSelection";

interface TrialShopSelectDialogProps {
  open: boolean;
  shops: TrialShopOption[];
  shopsLoading?: boolean;
  onConfirm: (shopName: string) => Promise<void>;
}

export function TrialShopSelectDialog({
  open,
  shops,
  shopsLoading = false,
  onConfirm,
}: TrialShopSelectDialogProps) {
  const { t } = useLanguage();
  const [selected, setSelected] = useState<string>(() => shops[0]?.shop_name ?? "");
  const [saving, setSaving] = useState(false);

  const effectiveSelected =
    shops.some((s) => s.shop_name === selected) ? selected : (shops[0]?.shop_name ?? "");

  const handleConfirm = async () => {
    if (!effectiveSelected) return;
    setSaving(true);
    try {
      await onConfirm(effectiveSelected);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={() => undefined}>
      <DialogContent
        className="sm:max-w-md"
        onPointerDownOutside={(e) => e.preventDefault()}
        onEscapeKeyDown={(e) => e.preventDefault()}
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Store className="h-5 w-5 text-primary" />
            {t("trialShop.title")}
          </DialogTitle>
          <DialogDescription className="whitespace-pre-line">{t("trialShop.description")}</DialogDescription>
        </DialogHeader>

        <RadioGroup
          value={effectiveSelected}
          onValueChange={setSelected}
          className="max-h-[50vh] overflow-y-auto space-y-2 py-1"
        >
          {shopsLoading ? (
            <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              {t("trialShop.loadingShops")}
            </div>
          ) : shops.length === 0 ? (
            <p className="py-4 text-sm text-muted-foreground text-center">{t("trialShop.noShopsYet")}</p>
          ) : (
            shops.map((shop) => (
              <label
                key={shop.shop_id}
                htmlFor={`trial-shop-${shop.shop_id}`}
                className="flex items-start gap-3 rounded-md border border-border p-3 cursor-pointer hover:bg-muted/50"
              >
                <RadioGroupItem
                  id={`trial-shop-${shop.shop_id}`}
                  value={shop.shop_name}
                  className="mt-0.5"
                />
                <div className="min-w-0">
                  <Label htmlFor={`trial-shop-${shop.shop_id}`} className="font-medium cursor-pointer">
                    {shop.shop_name}
                  </Label>
                </div>
              </label>
            ))
          )}
        </RadioGroup>

        <DialogFooter>
          <Button
            onClick={handleConfirm}
            disabled={shopsLoading || !effectiveSelected || saving}
            className="w-full sm:w-auto"
          >            {saving ? t("trialShop.saving") : t("trialShop.confirm")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
