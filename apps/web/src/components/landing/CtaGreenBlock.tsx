import { Link } from "react-router-dom";
import { Container } from "./Container";
import { useLanguage } from "@/contexts/LanguageContext";

const PLOV_IMG = "/plov.png";

interface CtaGreenBlockProps {
  onOpenAuth?: (tab: "signin" | "signup") => void;
  onOpenPromo?: () => void;
}

/**
 * CTA-блок под FAQ: ширина как у блока отзывов (max-w-5xl).
 * Слева — текст на зелёном фоне, справа — картинка плова на всю высоту блока.
 */
export function CtaGreenBlock({ onOpenAuth, onOpenPromo }: CtaGreenBlockProps) {
  const { language } = useLanguage();

  const mainText =
    language === "uz"
      ? "PROFiboard shaxsiy kabinetingizdagi barcha analitika rutinasini o‘z zimmasiga oladi va sizga eng muhimi — to‘g‘ri biznes‑qarorlar qabul qilish va foydani oshirishga e’tibor qaratishga yordam beradi!"
      : "PROFiboard возьмет на себя всю рутину аналитики вашего ЛК, позволив вам сосредоточиться на главном — принятии правильных бизнес-решений и увеличению прибыли!";
  const subText =
    language === "uz"
      ? "Tayyor yechimni atigi 2 ta kechki ovqat narxiga oling."
      : "получите готовое решение по цене 2x ужинов.";
  const buttonText =
    language === "uz" ? "BEPUL SINAB KO‘RISH" : "ПОПРОБОВАТЬ БЕСПЛАТНО";

  return (
    <section className="pt-8 sm:pt-10 md:pt-12 pb-16 sm:pb-20 md:pb-24 bg-white">
      <Container>
        <div className="max-w-5xl mx-auto overflow-hidden rounded-2xl sm:rounded-3xl flex flex-col md:flex-row min-h-[320px] md:min-h-[360px]">
          {/* Левая половина: текст */}
          <div className="flex-1 flex flex-col justify-center bg-[#c4ffdf] px-6 py-10 sm:px-10 sm:py-12 md:px-12 md:py-14">
            <p className="text-lg sm:text-xl md:text-[22px] leading-relaxed text-black">
              {mainText}
            </p>
            <p className="mt-5 text-base sm:text-lg md:text-[18px] text-black">
              {subText}
            </p>
            <div className="mt-8 flex justify-start">
              {onOpenPromo || onOpenAuth ? (
                <button
                  type="button"
                  className="inline-flex items-center justify-center h-12 px-8 rounded-xl bg-[#2C64ED] text-white font-medium uppercase tracking-wide hover:opacity-90 transition-opacity"
                  onClick={() => (onOpenPromo ? onOpenPromo() : onOpenAuth?.("signup"))}
                >
                  {buttonText}
                </button>
              ) : (
                <Link
                  to="/auth"
                  className="inline-flex items-center justify-center h-12 px-8 rounded-xl bg-[#2C64ED] text-white font-medium uppercase tracking-wide hover:opacity-90 transition-opacity"
                >
                  {buttonText}
                </Link>
              )}
            </div>
          </div>
          {/* Правая половина: картинка на всю высоту блока */}
          <div className="w-full md:w-1/2 flex-shrink-0 relative min-h-[240px] md:min-h-0 self-stretch">
            <img
              src={PLOV_IMG}
              alt="Плов"
              className="absolute inset-0 w-full h-full object-cover"
            />
          </div>
        </div>
      </Container>
    </section>
  );
}
