import { Link } from "react-router-dom";
import {
  ArrowRight,
  BarChart3,
  Check,
  ChevronDown,
  ChevronRight,
  KeyRound,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Container } from "./Container";
import { SectionTitle } from "./SectionTitle";
import { useLanguage } from "@/contexts/LanguageContext";

interface HowItWorksProps {
  onOpenAuth?: (tab: "signin" | "signup") => void;
  onOpenPromo?: () => void;
}

const contentRu = {
  title: "Как это работает",
  subtitle:
    "Подключите API Uzum Seller один раз и получайте актуальную аналитику.",
  flow: ["Подключение", "Синхронизация", "Аналитика"],
  cards: [
    {
      icon: KeyRound,
      title: "Подключите API Uzum",
      description:
        "Создайте API-ключ в личном кабинете Uzum Seller и добавьте его в PROFiboard.",
    },
    {
      icon: RefreshCw,
      title: "Автоматическая загрузка данных",
      description: "Продажи, расходы и остатки будут загружаться автоматически.",
    },
    {
      icon: BarChart3,
      title: "Готовая аналитика",
      description:
        "Контролируйте прибыль, расходы и эффективность товаров в одном месте.",
    },
  ],
  perks: [
    "Подключение через официальный API Uzum Seller",
    "Без ручной загрузки Excel-файлов",
    "Автоматическое обновление данных",
    "Безопасное хранение данных",
  ],
  cta: "Подключить API бесплатно",
};

const contentUz = {
  title: "Bu qanday ishlaydi",
  subtitle:
    "Uzum Seller API ni bir marta ulang va dolzarb tahlilni oling.",
  flow: ["Ulanish", "Sinxronizatsiya", "Tahlil"],
  cards: [
    {
      icon: KeyRound,
      title: "Uzum API ni ulang",
      description:
        "Uzum Seller shaxsiy kabinetida API kalit yarating va PROFiboard’ga qo‘shing.",
    },
    {
      icon: RefreshCw,
      title: "Avtomatik ma’lumot yuklash",
      description: "Savdolar, xarajatlar va qoldiqlar avtomatik yuklanadi.",
    },
    {
      icon: BarChart3,
      title: "Tayyor tahlil",
      description:
        "Foyda, xarajatlar va tovarlar samaradorligini bir joyda nazorat qiling.",
    },
  ],
  perks: [
    "Rasmiy Uzum Seller API orqali ulanish",
    "Excel fayllarni qo‘lda yuklamasdan",
    "Ma’lumotlarni avtomatik yangilash",
    "Ma’lumotlarni xavfsiz saqlash",
  ],
  cta: "API ni bepul ulash",
};

function StepCard({
  icon: Icon,
  title,
  description,
}: {
  icon: typeof KeyRound;
  title: string;
  description: string;
}) {
  return (
    <div className="flex h-full flex-col rounded-xl border border-border/80 bg-white p-4 shadow-sm sm:p-5">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
        <Icon className="h-5 w-5 text-primary" strokeWidth={2.25} aria-hidden />
      </div>
      <h3 className="mt-3 text-sm font-semibold leading-snug text-foreground sm:text-[15px]">
        {title}
      </h3>
      <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground sm:text-sm">
        {description}
      </p>
    </div>
  );
}

function FlowArrow({ vertical }: { vertical?: boolean }) {
  const Icon = vertical ? ChevronDown : ChevronRight;
  return (
    <div
      className={
        vertical
          ? "flex items-center justify-center py-1"
          : "flex items-center justify-center px-1"
      }
      aria-hidden
    >
      <Icon className="h-5 w-5 text-primary/55 shrink-0" />
    </div>
  );
}

/** Компактная секция «Как это работает» — три шага и CTA. */
export function HowItWorks({ onOpenAuth, onOpenPromo }: HowItWorksProps) {
  const { language } = useLanguage();
  const c = language === "uz" ? contentUz : contentRu;

  const ctaButtonClass =
    "bg-primary hover:bg-primary/90 text-primary-foreground font-semibold rounded-lg px-6";

  const cta =
    onOpenPromo || onOpenAuth ? (
      <Button
        size="lg"
        className={ctaButtonClass}
        onClick={() => (onOpenPromo ? onOpenPromo() : onOpenAuth?.("signup"))}
      >
        {c.cta}
        <ArrowRight className="ml-2 h-4 w-4" />
      </Button>
    ) : (
      <Button size="lg" className={ctaButtonClass} asChild>
        <Link to="/auth">
          {c.cta}
          <ArrowRight className="ml-2 h-4 w-4" />
        </Link>
      </Button>
    );

  return (
    <section
      id="how-it-works"
      className="-mt-2 md:-mt-4 pt-0 pb-10 sm:pb-12 md:pb-14 bg-white scroll-mt-20 sm:scroll-mt-24"
    >
      <Container>
        <SectionTitle
          title={c.title}
          subtitle={c.subtitle}
          className="mb-6 md:mb-7"
          titleClassName="text-2xl sm:text-3xl md:text-4xl leading-tight"
          subtitleClassName="mt-2 sm:mt-3 text-sm sm:text-base max-w-3xl"
        />

        <p className="mb-3 hidden md:block text-center text-xs font-semibold uppercase tracking-wide text-primary/75">
          {c.flow.join(" → ")}
        </p>

        {/* Desktop: cards with arrows */}
        <div className="hidden md:grid max-w-5xl mx-auto grid-cols-[1fr_auto_1fr_auto_1fr] gap-2 lg:gap-3 items-stretch">
          {c.cards.map((card, index) => (
            <div key={card.title} className="contents">
              <StepCard {...card} />
              {index < c.cards.length - 1 && <FlowArrow />}
            </div>
          ))}
        </div>

        {/* Mobile: stacked cards */}
        <div className="flex flex-col gap-1 md:hidden max-w-md mx-auto">
          {c.cards.map((card, index) => (
            <div key={card.title} className="flex flex-col">
              <p className="mb-1.5 text-center text-[11px] font-semibold uppercase tracking-wide text-primary/80">
                {c.flow[index]}
              </p>
              <StepCard {...card} />
              {index < c.cards.length - 1 && <FlowArrow vertical />}
            </div>
          ))}
        </div>

        <ul className="mt-6 md:mt-7 max-w-2xl mx-auto grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2">
          {c.perks.map((perk) => (
            <li key={perk} className="flex items-start gap-2 text-sm text-muted-foreground">
              <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" strokeWidth={2.5} aria-hidden />
              <span>{perk}</span>
            </li>
          ))}
        </ul>

        <div className="mt-6 md:mt-7 flex justify-center">{cta}</div>
      </Container>
    </section>
  );
}
