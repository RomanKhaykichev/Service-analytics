import { Link } from "react-router-dom";
import { Container } from "./Container";
import { useLanguage } from "@/contexts/LanguageContext";

/** Та же типографика, что у второго абзаца под превью дашборда в секции Features. */
const taglineClass =
  "text-center font-bold text-foreground max-w-5xl mx-auto text-lg sm:text-xl md:text-2xl leading-relaxed";

const taglineRu =
  "PROFiboard возьмет на себя всю рутину аналитики вашего ЛК, позволив вам сосредоточиться на главном — принятии правильных бизнес-решений и увеличению прибыли!";

const taglineUz =
  "PROFiboard shaxsiy kabinetingiz analitikasidagi rutina ishlarni o‘z zimmasiga oladi, siz esa asosiyga — to‘g‘ri biznes qarorlarini qabul qilish va foydani oshirishga jamlanishingiz mumkin!";

const ctaButtonClass =
  "inline-flex items-center justify-center h-12 px-8 rounded-xl bg-[#2C64ED] text-white font-semibold hover:opacity-90 transition-opacity";

interface LandingClosingTaglineProps {
  onOpenAuth?: (tab: "signin" | "signup") => void;
  onOpenPromo?: () => void;
}

export function LandingClosingTagline({ onOpenAuth, onOpenPromo }: LandingClosingTaglineProps) {
  const { language } = useLanguage();
  const text = language === "uz" ? taglineUz : taglineRu;
  const buttonText = language === "uz" ? "Bepul sinab ko‘rish" : "Попробовать бесплатно";

  return (
    <section className="bg-white pt-2 sm:pt-4 pb-10 sm:pb-12 md:pb-14">
      <Container>
        <div className="flex flex-col items-center">
          <p className={taglineClass}>{text}</p>
          <div className="mt-8 sm:mt-10 flex justify-center w-full">
            {onOpenPromo || onOpenAuth ? (
              <button
                type="button"
                className={ctaButtonClass}
                onClick={() => (onOpenPromo ? onOpenPromo() : onOpenAuth?.("signup"))}
              >
                {buttonText}
              </button>
            ) : (
              <Link to="/auth" className={ctaButtonClass}>
                {buttonText}
              </Link>
            )}
          </div>
        </div>
      </Container>
    </section>
  );
}
