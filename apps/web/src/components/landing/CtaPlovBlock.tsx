import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import styles from "./CtaPlovBlock.module.css";

/** Картинка плова в public/plov.png */
const PLOV_IMG = "/plov.png";

/**
 * Один CTA-блок: общий контейнер .cta, контент рендерится один раз, без второго фона и дублирования.
 */
export function CtaPlovBlock() {
  return (
    <section className="bg-white py-16 sm:py-20 md:py-24">
      <div className="mx-auto max-w-5xl px-4 sm:px-6">
        <div className={styles.cta}>
          <div className={styles.content}>
            <p className="text-[22px] md:text-[26px] leading-[1.25] text-black text-left md:text-center">
              <span className="font-extrabold">PROF</span>i<span className="font-semibold">board</span>{" "}
              возьмет на себя всю рутину аналитики вашего ЛК, позволив вам
              сосредоточиться на главном — принятии правильных бизнес-решений и
              увеличению прибыли!
            </p>

            <p className="mt-6 text-[18px] md:text-[20px] text-black/90 text-left md:text-center">
              получите готовое решение по цене 2х ужинов.
            </p>

            <div className="mt-8 flex justify-start md:justify-center">
              <Link to="/auth">
                <Button
                  type="button"
                  className="h-[48px] rounded-[14px] px-8 text-white font-semibold uppercase tracking-wide bg-[#2055E5]"
                >
                  ПОПРОБОВАТЬ БЕСПЛАТНО
                </Button>
              </Link>
            </div>
          </div>

          <div className={styles.media} aria-hidden="true">
            <img
              className={styles.image}
              src={PLOV_IMG}
              alt="Плов"
            />
          </div>
        </div>
      </div>
    </section>
  );
}
