import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Container } from "./Container";
import { ArrowRight } from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";

interface HeroProps {
  onOpenAuth?: (tab: "signin" | "signup") => void;
  onOpenPromo?: () => void;
}

/** Hero: заголовок, лозунг, CTA и фото. На lg+ — ряд как на десктопе; на телефоне — колонка без обрезки и налезания CTA. */
export function Hero({ onOpenAuth, onOpenPromo }: HeroProps) {
  const { language } = useLanguage();

  const title =
    language === "uz"
      ? "Siz UZUM Market’da sotuvchisizmi? Haqiqiy foydangizni aniq bilasizmi?"
      : "Вы продавец на UZUM Market? Уверены что знаете свою реальную прибыль?";
  const description =
    language === "uz"
      ? "PROFiboard sizning foydangizni, marginallikni va zarar keltirayotgan tovarlarni bir necha bosishda ko‘rsatib beradi."
      : "PROFiboard показывает реальную прибыль, маржинальность и убыточные товары в вашем магазине — в несколько кликов.";
  const ctaLabel = language === "uz" ? "SINAB KO‘RISH" : "ПОПРОБОВАТЬ";

  const ctaButtonClass =
    "bg-[#3366FF] hover:bg-[#2952CC] text-white font-semibold uppercase tracking-wide rounded-lg px-6";

  const cta =
    onOpenPromo || onOpenAuth ? (
      <Button
        size="lg"
        className={ctaButtonClass}
        onClick={() => (onOpenPromo ? onOpenPromo() : onOpenAuth?.("signup"))}
      >
        {ctaLabel} <ArrowRight className="ml-2 h-4 w-4 inline" />
      </Button>
    ) : (
      <Link to="/auth">
        <Button size="lg" className={ctaButtonClass}>
          {ctaLabel} <ArrowRight className="ml-2 h-4 w-4 inline" />
        </Button>
      </Link>
    );

  return (
    <section className="relative overflow-hidden bg-white pt-3 sm:pt-4 lg:pt-0 pb-4 sm:pb-5 md:pb-6 lg:pb-8 scroll-mt-16">
      <Container className="relative flex flex-col gap-1 lg:gap-2">
        <div className="flex flex-col items-stretch gap-8 lg:flex-row lg:items-center lg:gap-12">
          <div className="min-w-0 flex-1 text-left max-w-2xl lg:max-w-3xl lg:-mr-12 xl:-mr-20 z-10 lg:pr-4 lg:ml-16 xl:ml-24 lg:-mt-6">
            <h1 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold text-foreground tracking-tight leading-tight">
              {title}
            </h1>
            <p className="mt-5 sm:mt-6 text-base sm:text-lg text-foreground">
              {description}
            </p>
            {/* На телефоне кнопка сразу под текстом — без отрицательных margin и налезания */}
            <div className="mt-8 flex w-full justify-center lg:hidden">{cta}</div>
          </div>
          <div className="relative z-0 flex w-full shrink-0 justify-center lg:mx-0 lg:ml-8 lg:mt-0 lg:w-auto lg:max-w-sm lg:flex-1 lg:justify-end xl:ml-12">
            <div className="relative aspect-square w-full max-w-[min(100%,20rem)] rounded-full bg-sky-100 overflow-hidden flex items-center justify-center sm:max-w-sm">
              <img
                src="/hero-seller.png"
                alt="Продавец с телефоном"
                className="h-full w-full object-cover object-center"
              />
            </div>
          </div>
        </div>
        {/* На десктопе — прежнее перекрытие с блоком ниже */}
        <div className="hidden w-full justify-center lg:flex -mt-10 lg:-mt-16">{cta}</div>
      </Container>
    </section>
  );
}
