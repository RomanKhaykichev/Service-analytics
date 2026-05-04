import { useEffect, useRef, useState } from "react";
import { Container } from "./Container";
import { SectionTitle } from "./SectionTitle";
import { useLanguage } from "@/contexts/LanguageContext";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

const IMPORT_REPORTS_VIDEO_SRC = "/videos/01-import-reports.mp4";

const stepsRu = [
  {
    step: 1,
    title: "Сформируйте 4 отчета в ЛК продавца.",
    text: "Отчет о продажах, отчет об услугах, отчет об остатках (старого формата), отчет о хранении.",
    image: "/how-it-works-1.png",
  },
  {
    step: 2,
    title: "Загрузите 4 отчета в PROFiboard.",
    text: "Важно! Отчеты должны быть все одного периода. Мы рекомендуем выгружать отчеты с начала года.",
    image: "/how-it-works-2.png",
  },
  {
    step: 3,
    title: "Отслеживайте ваши успехи.",
    text: "Используйте данные чтобы оптимизировать расходы. Следите как меняется ваша прибыль от месяца к месяцу.",
    image: "/how-it-works-3.png",
  },
];

const stepsUz = [
  {
    step: 1,
    title: "Sotuvchi SK’sida 4 ta hisobotni shakllantiring.",
    text: "Savdolar hisobotini, xizmatlar bo‘yicha hisobotni, qoldiqlar hisobotini (eski format), saqlash bo‘yicha hisobotni yuklab oling.",
    image: "/how-it-works-1.png",
  },
  {
    step: 2,
    title: "Ushbu 4 ta hisobotni PROFiboard’ga yuklang.",
    text: "Muhim! Hisobotlarning barchasi bir davr uchun bo‘lishi kerak. Biz hisobotlarni yil boshidan boshlab yuklashni tavsiya qilamiz.",
    image: "/how-it-works-2.png",
  },
  {
    step: 3,
    title: "Natijalaringizni kuzatib boring.",
    text: "Ma’lumotlardan xarajatlarni optimallashtirish uchun foydalaning. Foydangiz oyma‑oy qanday o‘zgarayotganini kuzating.",
    image: "/how-it-works-3.png",
  },
];

/** Секция «Как это работает» — формирование отчётов, загрузка в PROFiboard, дашборды. */
export function HowItWorks() {
  const { language } = useLanguage();
  const [videoOpen, setVideoOpen] = useState(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const steps = language === "uz" ? stepsUz : stepsRu;
  const title = language === "uz" ? "Bu qanday ishlaydi" : "Как это работает";
  const subtitle =
    language === "uz"
      ? "Birinchi hisobotlargacha atigi uchta oddiy qadam"
      : "Три простых шага до первых отчётов";
  const watchVideoLabel = language === "uz" ? "Videoni tomosha qilish" : "Смотреть видео";
  const importVideoTitle =
    language === "uz" ? "Hisobotlarni import qilish" : "Импорт отчётов";

  useEffect(() => {
    if (!videoOpen) {
      videoRef.current?.pause();
      return;
    }

    let removeCanPlay: (() => void) | undefined;
    let raf = 0;

    const start = (v: HTMLVideoElement) => {
      const tryPlay = () => {
        void v.play().catch(() => {});
      };
      v.currentTime = 0;
      if (v.readyState >= 3) {
        requestAnimationFrame(tryPlay);
        return;
      }
      const onCanPlay = () => tryPlay();
      v.addEventListener("canplay", onCanPlay, { once: true });
      removeCanPlay = () => v.removeEventListener("canplay", onCanPlay);
    };

    const v = videoRef.current;
    if (v) {
      start(v);
    } else {
      raf = requestAnimationFrame(() => {
        const el = videoRef.current;
        if (el) start(el);
      });
    }

    return () => {
      cancelAnimationFrame(raf);
      removeCanPlay?.();
    };
  }, [videoOpen]);

  return (
    <section id="how-it-works" className="-mt-2 md:-mt-4 pt-0 pb-16 sm:pb-20 md:pb-24 bg-white scroll-mt-20 sm:scroll-mt-24">
      <Container>
        <SectionTitle title={title} className="mb-0" titleClassName="leading-none pb-px" />
        <div className="mt-0 flex flex-wrap items-center justify-center gap-x-3 gap-y-1.5 text-center">
          <p className="text-base sm:text-lg text-muted-foreground max-w-2xl">
            {subtitle}
          </p>
          <button
            type="button"
            onClick={() => setVideoOpen(true)}
            className="shrink-0 text-base font-medium text-primary underline underline-offset-4 hover:text-primary/90"
          >
            {watchVideoLabel}
          </button>
        </div>
        <Dialog open={videoOpen} onOpenChange={setVideoOpen}>
          <DialogContent className="max-w-4xl w-[calc(100vw-2rem)] gap-0 p-0 sm:max-w-4xl overflow-hidden">
            <DialogHeader className="px-4 pt-4 pb-3 text-left">
              <DialogTitle>{importVideoTitle}</DialogTitle>
            </DialogHeader>
            <div className="px-4 pb-4">
              <video
                ref={videoRef}
                src={IMPORT_REPORTS_VIDEO_SRC}
                controls
                playsInline
                className="w-full rounded-md bg-black"
                preload="auto"
              >
                {language === "uz" ? "Brauzeringiz video qo‘llab-quvvatlamaydi." : "Ваш браузер не поддерживает видео."}
              </video>
            </div>
          </DialogContent>
        </Dialog>
        <div className="relative grid grid-cols-1 md:grid-cols-3 gap-8 md:gap-10 mt-8 md:mt-10">
          {/* Линия между кружком 1 и 2 (не пересекает кружки) */}
          <div
            className="absolute top-6 left-[calc(16.666%+1.5rem)] right-[calc(50%+1.5rem)] h-0.5 bg-border z-0 hidden md:block"
            aria-hidden
          />
          {/* Линия между кружком 2 и 3 */}
          <div
            className="absolute top-6 left-[calc(50%+1.5rem)] right-[calc(16.666%+1.5rem)] h-0.5 bg-border z-0 hidden md:block"
            aria-hidden
          />
          {steps.map((item) => (
            <div key={item.step} className="relative z-10 flex flex-col text-center">
              <div className="mx-auto flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground font-bold text-lg">
                {item.step}
              </div>
              <div className="mt-4 rounded-lg border bg-muted/30 overflow-hidden h-52 md:h-56 flex items-center justify-center">
                <img
                  src={item.image}
                  alt=""
                  className="max-h-full w-auto object-contain"
                />
              </div>
              <h3 className="mt-4 font-semibold text-foreground">{item.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{item.text}</p>
            </div>
          ))}
        </div>
      </Container>
    </section>
  );
}
