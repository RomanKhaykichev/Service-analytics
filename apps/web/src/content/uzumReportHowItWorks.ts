export type AppLanguage = "ru" | "uz";
export const IMPORT_REPORTS_VIDEO_SRC = "/videos/01-import-reports.mp4";

export type UzumHowItWorksStep = {
  step: number;
  title: string;
  text: string;
  image: string;
  /** Доп. скриншоты подряд в том же блоке (напр. выбор типов отчёта в ЛК Uzum). */
  additionalImages?: string[];
  /** Текст сразу под заголовком шага (только в окне загрузки с подсказкой). */
  noticeUnderTitle?: string;
};

const stepsRu: UzumHowItWorksStep[] = [
  {
    step: 1,
    title: "Скачайте 4 отчета в личном кабинете Uzum.",
    noticeUnderTitle:
      "Важно! Отчеты должны быть все одного периода. Мы рекомендуем выгружать отчеты с начала года.",
    text: "1. Сформируйте 4 отчета XLSX (Отчет о продажах, отчет об услугах, отчет об остатках (старого формата), отчет о хранении.)\n2. Сохраните у себя на компьютере.",
    image: "/how-it-works-1.png",
    additionalImages: ["/how-it-works-uzum-lk-report-modal.png"],
  },
  {
    step: 2,
    title: "Загрузите 4 отчета в PROFiboard.",
    text: "1. Нажмите на кнопку Загрузить отчеты в шапке сервиса PROFiboard.\n2. Перетащите файлы или нажмите на окно загрузки.",
    image: "/how-it-works-2.png",
    additionalImages: ["/how-it-works-profiboard-upload-drag.png"],
  },
  {
    step: 3,
    title: "Отслеживайте ваши успехи.",
    text: "Используйте данные чтобы оптимизировать расходы. Следите как меняется ваша прибыль от месяца к месяцу.",
    image: "/how-it-works-3.png",
  },
];

const stepsUz: UzumHowItWorksStep[] = [
  {
    step: 1,
    title: "Uzum shaxsiy kabinetidan 4 ta hisobotni yuklab oling.",
    noticeUnderTitle:
      "Muhim! Hisobotlarning barchasi bir davr uchun bo‘lishi kerak. Biz hisobotlarni yil boshidan boshlab yuklashni tavsiya qilamiz.",
    text: "1. 4 ta XLSX hisobotni shakllantiring (Savdolar hisobotini, xizmatlar bo‘yicha hisobotni, qoldiqlar hisobotini (eski format), saqlash bo‘yicha hisobotni.)\n2. Ularni kompyuteringizga saqlang.",
    image: "/how-it-works-1.png",
    additionalImages: ["/how-it-works-uzum-lk-report-modal.png"],
  },
  {
    step: 2,
    title: "Ushbu 4 ta hisobotni PROFiboard’ga yuklang.",
    text: "1. PROFiboard xizmati sarlavhasidagi «Hisobotlarni yuklash» tugmasini bosing.\n2. Fayllarni sudrab tashlang yoki yuklash oynasini (maydonchasini) bosing.",
    image: "/how-it-works-2.png",
    additionalImages: ["/how-it-works-profiboard-upload-drag.png"],
  },
  {
    step: 3,
    title: "Natijalaringizni kuzatib boring.",
    text: "Ma’lumotlardan xarajatlarni optimallashtirish uchun foydalaning. Foydangiz oyma‑oy qanday o‘zgarayotganini kuzating.",
    image: "/how-it-works-3.png",
  },
];

export function getUzumReportHowItWorksSteps(language: AppLanguage): UzumHowItWorksStep[] {
  return language === "uz" ? stepsUz : stepsRu;
}

export function getStepVisualImageUrls(step: UzumHowItWorksStep): string[] {
  return [step.image, ...(step.additionalImages ?? [])];
}
