import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Цвет габаритной группы: отображение из файла (UZ — KGT/OʻGT/BGT, RU — СГТ/МГТ/БГТ),
 * цвет по сопоставлению с русским. По файлам seller-storage: KGT (UZ)=МГТ (RU), OʻGT (UZ)=СГТ (RU), BGT=БГТ.
 */
export function getSizeGroupColorClass(sizeGroup: string | null | undefined): string {
  if (!sizeGroup || sizeGroup.trim() === "" || sizeGroup.trim() === "-") {
    return "bg-muted/60 text-muted-foreground";
  }
  const s = sizeGroup.trim();
  const lower = s.toLowerCase();
  const lowerNorm = lower.replace(/\u02bb/g, "'").replace(/\u2019/g, "'");
  // RU: СГТ (малая), МГТ (средняя), БГТ (большая). UZ по выгрузкам: OʻGT/OGT=СГТ, KGT=МГТ, BGT=БГТ
  const isSmall = s === "СГТ" || lower === "mgt" || lowerNorm === "o'gt" || lowerNorm === "ogt" || lower.includes("kichik");
  const isMedium = s === "МГТ" || lower === "kgt" || lower.includes("o'rta") || lower.includes("orta");
  const isLarge = s === "БГТ" || lower === "bgt" || lower.includes("katta");
  if (isSmall) return "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400";
  if (isMedium) return "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400";
  if (isLarge) return "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400";
  return "bg-muted/60 text-muted-foreground";
}
