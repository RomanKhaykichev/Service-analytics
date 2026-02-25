import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Container } from "./Container";
import { ArrowRight } from "lucide-react";

interface HeroProps {
  onOpenAuth?: (tab: 'signin' | 'signup') => void;
}

/** Hero-секция: вопрос для продавцов UZUM, описание PROFiboard, CTA и изображение. */
export function Hero({ onOpenAuth }: HeroProps) {
  return (
    <section className="relative overflow-hidden bg-white pt-0 pb-4 sm:pb-5 md:pb-6 lg:pb-8">
      <Container className="relative flex flex-col gap-1 lg:gap-2">
        <div className="flex flex-col lg:flex-row items-center gap-12 lg:gap-8">
          <div className="flex-1 text-left max-w-2xl lg:max-w-3xl lg:-mr-12 xl:-mr-20 z-10 lg:pr-4 lg:ml-16 xl:ml-24 -mt-4 sm:-mt-6">
            <h1 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold text-foreground tracking-tight leading-tight">
              Вы продавец на UZUM Market? Уверены что знаете свою реальную прибыль?
            </h1>
            <p className="mt-5 sm:mt-6 text-base sm:text-lg text-foreground">
              PROFiboard показывает реальную прибыль, маржинальность и убыточные товары в вашем магазине — в несколько кликов.
            </p>
          </div>
          <div className="flex-1 flex justify-center lg:justify-end w-full max-w-md relative z-0 lg:ml-8 xl:ml-12 mt-6 lg:mt-10">
            <div className="relative w-full max-w-sm aspect-square rounded-full bg-sky-100 overflow-hidden flex items-center justify-center">
              <img
                src="/hero-seller.png"
                alt="Продавец с телефоном"
                className="w-full h-full object-cover object-center"
              />
            </div>
          </div>
        </div>
        <div className="w-full flex justify-center -mt-10 lg:-mt-16">
          {onOpenAuth ? (
            <Button
              size="lg"
              className="bg-[#3366FF] hover:bg-[#2952CC] text-white font-semibold uppercase tracking-wide rounded-lg px-6"
              onClick={() => onOpenAuth('signup')}
            >
              ПОПРОБОВАТЬ <ArrowRight className="ml-2 h-4 w-4 inline" />
            </Button>
          ) : (
            <Link to="/auth">
              <Button
                size="lg"
                className="bg-[#3366FF] hover:bg-[#2952CC] text-white font-semibold uppercase tracking-wide rounded-lg px-6"
              >
                ПОПРОБОВАТЬ <ArrowRight className="ml-2 h-4 w-4 inline" />
              </Button>
            </Link>
          )}
        </div>
      </Container>
    </section>
  );
}
