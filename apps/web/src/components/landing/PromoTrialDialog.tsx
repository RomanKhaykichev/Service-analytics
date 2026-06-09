import {
  Dialog,
  DialogContent,
  DialogHeader,
} from "@/components/ui/dialog";
import { Fragment, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import {
  Box,
  Calendar,
  Clock,
  LineChart,
  Percent,
  Shield,
  Star,
  Store,
  Wallet,
  Warehouse,
} from "lucide-react";
import { apiPostNoAuth, getVisitorKey } from "@/lib/api";
import { useLanguage } from "@/contexts/LanguageContext";

interface PromoTrialDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onTryFree: () => void;
}

const PURPLE = "#5D3FD3";

const copy = {
  ru: {
    headlineBefore: "Найдите ",
    headlineHighlight1: "убыточные товары",
    headlineMiddle: " и ",
    headlineHighlight2: "скрытые расходы",
    subtitle: "Получите готовую аналитику вашего магазина на Uzum.",
    features: [
      {
        line1: "Реальная прибыль",
        line2: "по товарам",
        bg: "bg-emerald-100",
        color: "text-emerald-600",
        Icon: LineChart,
      },
      {
        line1: "Все расходы и комиссии",
        line2: "Uzum",
        bg: "bg-violet-100",
        color: "text-violet-600",
        Icon: Percent,
      },
      {
        line1: "Топ прибыльные товары",
        line2: "и категории",
        bg: "bg-sky-100",
        color: "text-sky-600",
        Icon: Star,
      },
      {
        line1: "Остатки и хранение",
        line2: "под контролем",
        bg: "bg-orange-100",
        color: "text-orange-600",
        Icon: Box,
      },
    ],
    insightsTitle: "Какие инсайты вы получите",
    insights: [
      {
        kind: "storage" as const,
        highlight: "уменьшились на 4.1%",
        amount: "7 245",
      },
      {
        kind: "minProfit" as const,
        product: "Чехол iPhone",
        amount: "169 300",
      },
      {
        kind: "maxProfit" as const,
        product: "Наушники AirPods",
        amount: "544 700",
      },
    ],
    trust: [
      { Icon: Calendar, line1: "10 дней", line2: "бесплатно", iconClass: "text-violet-600" },
      { Icon: Store, line1: "1 магазин", line2: "в trial", iconClass: "text-violet-600" },
      { Icon: Clock, line1: "60 дней", line2: "данных", iconClass: "text-violet-600" },
      { Icon: Shield, line1: "Безопасно", line2: "и надежно", iconClass: "text-emerald-600" },
    ],
    cta: "Получить доступ",
  },
  uz: {
    headlineBefore: "Zarar keltiradigan tovarlar va ",
    headlineHighlight1: "yashirin xarajatlarni",
    headlineMiddle: " ",
    headlineHighlight2: "toping",
    subtitle: "Uzum do‘koningiz uchun tayyor analitikani 2 daqiqada oling",
    features: [
      {
        line1: "Haqiqiy foyda",
        line2: "tovarlar bo‘yicha",
        bg: "bg-emerald-100",
        color: "text-emerald-600",
        Icon: LineChart,
      },
      {
        line1: "Barcha xarajat va komissiyalar",
        line2: "Uzum",
        bg: "bg-violet-100",
        color: "text-violet-600",
        Icon: Percent,
      },
      {
        line1: "Eng foydali tovarlar",
        line2: "va kategoriyalar",
        bg: "bg-sky-100",
        color: "text-sky-600",
        Icon: Star,
      },
      {
        line1: "Qoldiq va saqlash",
        line2: "nazoratda",
        bg: "bg-orange-100",
        color: "text-orange-600",
        Icon: Box,
      },
    ],
    insightsTitle: "Qanday insaytlar olasiz",
    insights: [
      {
        kind: "storage" as const,
        highlight: "4.1% ga kamaydi",
        amount: "7 245",
      },
      {
        kind: "minProfit" as const,
        product: "iPhone qopqog‘i",
        amount: "169 300",
      },
      {
        kind: "maxProfit" as const,
        product: "AirPods naushniklari",
        amount: "544 700",
      },
    ],
    trust: [
      { Icon: Calendar, line1: "10 kun", line2: "bepul", iconClass: "text-violet-600" },
      { Icon: Store, line1: "1 do‘kon", line2: "trialda", iconClass: "text-violet-600" },
      { Icon: Clock, line1: "60 kun", line2: "maʼlumotlar", iconClass: "text-violet-600" },
      { Icon: Shield, line1: "Xavfsiz", line2: "va ishonchli", iconClass: "text-emerald-600" },
    ],
    cta: "Kirish olish",
  },
} as const;

type InsightItem = (typeof copy.ru.insights)[number];

const insightIcons: Record<
  InsightItem["kind"],
  { Icon: typeof Warehouse; iconClass: string }
> = {
  storage: { Icon: Warehouse, iconClass: "text-violet-600" },
  minProfit: { Icon: Wallet, iconClass: "text-red-500" },
  maxProfit: { Icon: Wallet, iconClass: "text-emerald-600" },
};

function InsightRow({
  item,
  language,
}: {
  item: InsightItem;
  language: "ru" | "uz";
}) {
  const { Icon, iconClass } = insightIcons[item.kind];
  const currency = language === "uz" ? "so‘m" : "сум";

  let text: ReactNode;
  if (item.kind === "storage") {
    text =
      language === "uz" ? (
        <>
          Saqlash xarajatlari{" "}
          <span className="font-semibold text-emerald-600">{item.highlight}</span>{" "}
          <span className="text-zinc-500">(-{item.amount} {currency})</span>
        </>
      ) : (
        <>
          Расходы за хранение{" "}
          <span className="font-semibold text-emerald-600">{item.highlight}</span>{" "}
          <span className="text-zinc-500">(-{item.amount} {currency})</span>
        </>
      );
  } else if (item.kind === "minProfit") {
    text =
      language === "uz" ? (
        <>
          «{item.product}» tovari minimal foyda keltirdi{" "}
          <span className="font-semibold text-red-500">
            ({item.amount} {currency})
          </span>
        </>
      ) : (
        <>
          Товар «{item.product}» принес минимальную прибыль{" "}
          <span className="font-semibold text-red-500">
            ({item.amount} {currency})
          </span>
        </>
      );
  } else {
    text =
      language === "uz" ? (
        <>
          «{item.product}» eng foydali tovarga aylandi{" "}
          <span className="font-semibold text-emerald-600">
            (+{item.amount} {currency})
          </span>
        </>
      ) : (
        <>
          Товар «{item.product}» стал самым прибыльным{" "}
          <span className="font-semibold text-emerald-600">
            (+{item.amount} {currency})
          </span>
        </>
      );
  }

  return (
    <li className="flex gap-1.5 text-[9px] sm:text-[10px] text-zinc-700 leading-snug">
      <Icon className={`mt-px h-3 w-3 shrink-0 ${iconClass}`} strokeWidth={1.75} />
      <span>{text}</span>
    </li>
  );
}

/**
 * Промо-окно перед регистрацией: условия триала и превью аналитики.
 * По кнопке CTA закрывает окно и вызывает onTryFree (открытие регистрации).
 */
export function PromoTrialDialog({
  open,
  onOpenChange,
  onTryFree,
}: PromoTrialDialogProps) {
  const { language } = useLanguage();
  const lang = language === "uz" ? "uz" : "ru";
  const t = copy[lang];

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
        className="max-w-xl max-h-[88vh] p-0 gap-0 overflow-y-auto bg-white border border-border shadow-lg sm:rounded-lg"
        hideCloseButton
      >
        <DialogHeader className="sr-only">
          <span>PROFiboard</span>
        </DialogHeader>

        <div className="p-3 sm:p-4 flex flex-col">
          <div className="flex flex-col items-center text-center">
            <img
              src="/favicon.png"
              alt=""
              className="h-7 w-7 object-contain"
              aria-hidden
            />
            <h2 className="mt-0.5 text-base text-zinc-800">
              <span className="font-bold">PROFi</span>
              <span className="font-normal">board</span>
            </h2>
          </div>

          <h3 className="mt-2.5 text-center text-base sm:text-lg font-bold text-zinc-800 leading-snug">
            {t.headlineBefore}
            <span style={{ color: PURPLE }}>{t.headlineHighlight1}</span>
            {t.headlineMiddle}
            <span style={{ color: PURPLE }}>{t.headlineHighlight2}</span>
          </h3>
          <p className="mt-1 text-center text-xs text-zinc-500">{t.subtitle}</p>

          <div className="mt-3 flex flex-col sm:flex-row sm:items-start gap-3 sm:gap-4">
            <div className="sm:basis-[42%] shrink-0 grid grid-cols-2 gap-x-2 gap-y-2.5 sm:flex sm:flex-col sm:gap-2.5">
              {t.features.map(({ line1, line2, bg, color, Icon }) => (
                <div key={line1} className="flex items-center gap-2 min-w-0">
                  <div
                    className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${bg} ${color}`}
                  >
                    <Icon className="h-3.5 w-3.5" strokeWidth={1.75} />
                  </div>
                  <div className="min-w-0 text-left leading-tight">
                    <p className="text-[11px] font-bold text-zinc-800">{line1}</p>
                    <p className="text-[10px] text-zinc-500">{line2}</p>
                  </div>
                </div>
              ))}
            </div>
            <div className="sm:basis-[58%] min-w-0 rounded-xl border border-zinc-200 bg-zinc-50/60 p-2.5 sm:p-3">
              <p className="text-xs font-semibold" style={{ color: PURPLE }}>
                {t.insightsTitle}
              </p>
              <ul className="mt-2 space-y-2">
                {t.insights.map((item) => (
                  <InsightRow key={item.kind} item={item} language={lang} />
                ))}
              </ul>
            </div>
          </div>

          {/* Условия trial */}
          <div className="mt-3 rounded-xl border border-zinc-200 bg-white px-3 py-2.5 sm:px-4 sm:py-3">
            <div className="flex items-center justify-center overflow-x-auto">
              {t.trust.map(({ Icon, line1, line2, iconClass }, index) => (
                <Fragment key={line1}>
                  {index > 0 && (
                    <span className="mx-2 sm:mx-3 text-zinc-300 select-none shrink-0 text-xs" aria-hidden>
                      •
                    </span>
                  )}
                  <div className="flex items-center gap-1.5 shrink-0">
                    <Icon className={`h-4 w-4 shrink-0 ${iconClass}`} strokeWidth={1.75} />
                    <div className="text-left leading-tight">
                      <p className="text-xs font-bold text-zinc-800">{line1}</p>
                      <p className="text-[10px] text-zinc-500">{line2}</p>
                    </div>
                  </div>
                </Fragment>
              ))}
            </div>
          </div>

          <Button
            type="button"
            className="mt-3 w-full h-9 rounded-lg bg-[#28a745] hover:bg-[#218838] text-white font-semibold text-sm"
            onClick={handleTryFree}
          >
            {t.cta}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
