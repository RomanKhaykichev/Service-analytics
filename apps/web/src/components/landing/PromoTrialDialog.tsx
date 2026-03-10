import {
  Dialog,
  DialogContent,
  DialogHeader,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { BarChart3, Calendar, Store, Check } from "lucide-react";
import { apiPostNoAuth, getVisitorKey } from "@/lib/api";
import { useLanguage } from "@/contexts/LanguageContext";

interface PromoTrialDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onTryFree: () => void;
}

/**
 * Промо-окно перед регистрацией: условия триала (7 дней, 1 магазин, 30 дней данных).
 * По кнопке «Попробовать бесплатно» закрывает окно и вызывает onTryFree (открытие регистрации).
 */
export function PromoTrialDialog({
  open,
  onOpenChange,
  onTryFree,
}: PromoTrialDialogProps) {
  const { language } = useLanguage();

  const titleText =
    language === "uz"
      ? "PROFiboard — bepul sinab ko‘ring"
      : "PROFiboard — попробовать бесплатно";
  const subtitleTextRu =
    "Контролируйте прибыль вашего магазина на Uzum";
  const subtitleTextUz =
    "Uzum’dagi do‘koningizning foydasini nazorat qiling";
  const subtitleText = language === "uz" ? subtitleTextUz : subtitleTextRu;
  const trialLineText =
    language === "uz"
      ? "10 kun bepul • 1 do‘kon • 60 kunlik maʼlumotlar"
      : "10 дней бесплатно • 1 магазин • 60 дней данных";
  const buttonText =
    language === "uz" ? "Bepul sinab ko‘rish" : "Попробовать бесплатно";
  const daysLabel = language === "uz" ? "Kun" : "Дней";
  const daysFreeLabel =
    language === "uz" ? "Kun bepul" : "Дней бесплатно";
  const shopLabel = language === "uz" ? "Do‘kon" : "Магазин";
  const oneShopLabel =
    language === "uz" ? "1 do‘kon" : "1 Магазин";

  const handleTryFree = async () => {
    try {
      await apiPostNoAuth("/api/track/promo-try", {
        visitor_key: getVisitorKey(),
      });
    } catch {
      // ignore
    }
    onOpenChange(false);
    onTryFree();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-lg p-0 gap-0 overflow-hidden bg-white border border-border shadow-lg sm:rounded-lg"
        hideCloseButton
      >
        <DialogHeader className="sr-only">
          <span>{titleText}</span>
        </DialogHeader>
        <div className="p-6 sm:p-8 flex flex-col items-center text-center">
          {/* Иконка — favicon */}
          <img
            src="/favicon.png"
            alt=""
            className="h-14 w-14 object-contain"
            aria-hidden
          />
          <h2 className="mt-0.5 text-2xl text-zinc-800">
            <span className="font-bold">PROFi</span>
            <span className="font-normal">board</span>
          </h2>
          <p className="mt-1 text-base sm:text-lg font-bold text-zinc-700">
            {subtitleText}
          </p>
          <p className="mt-1 text-xs text-zinc-500">{trialLineText}</p>

          {/* Кнопка */}
          <Button
            type="button"
            className="mt-6 w-full max-w-xs h-12 rounded-xl bg-[#22c55e] hover:bg-[#16a34a] text-white font-semibold uppercase tracking-wide"
            onClick={handleTryFree}
          >
            {buttonText}
          </Button>

          {/* Карточки */}
          <div className="mt-6 grid grid-cols-3 gap-3 w-full">
            <div className="rounded-xl border border-zinc-200 bg-white p-3 flex flex-col items-center text-center">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100 text-green-600">
                <Calendar className="h-5 w-5" />
              </div>
              <span className="mt-2 text-lg font-bold text-zinc-800">10</span>
              <span className="text-xs text-zinc-600">{daysLabel}</span>
              <span className="mt-1 flex items-center justify-center gap-1 text-xs font-bold text-zinc-600 whitespace-nowrap">
                <Check className="h-3.5 w-3.5 text-green-600 shrink-0" />
                {daysFreeLabel}
              </span>
            </div>
            <div className="rounded-xl border border-zinc-200 bg-white p-3 flex flex-col items-center text-center">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-blue-600">
                <Store className="h-5 w-5" />
              </div>
              <span className="mt-2 text-lg font-bold text-zinc-800">1</span>
              <span className="text-xs text-zinc-600">{shopLabel}</span>
              <span className="mt-1 flex items-center justify-center gap-1 text-xs font-bold text-zinc-600 whitespace-nowrap">
                <Check className="h-3.5 w-3.5 text-green-600 shrink-0" />
                {oneShopLabel}
              </span>
            </div>
            <div className="rounded-xl border border-zinc-200 bg-white p-3 flex flex-col items-center text-center">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-violet-100 text-violet-600">
                <BarChart3 className="h-5 w-5" />
              </div>
              <span className="mt-2 text-lg font-bold text-zinc-800">60</span>
              <span className="text-xs text-zinc-600">{daysLabel}</span>
              <span className="mt-1 flex items-center justify-center gap-1 text-xs font-bold text-zinc-600 whitespace-nowrap">
                <Check className="h-3.5 w-3.5 text-green-600 shrink-0" />
                {language === "uz" ? "60 kunlik maʼlumotlar" : "60 Дней данных"}
              </span>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
