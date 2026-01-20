/**
 * Безопасное преобразование значения в число
 */
export function safeNumber(v: unknown): number {
  if (v == null || v === undefined) {
    return 0;
  }
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

/**
 * Форматирование числа с разделителями тысяч
 */
export function formatNumber(value?: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  const num = safeNumber(value);
  if (!Number.isFinite(num) || Number.isNaN(num)) {
    return "—";
  }
  return new Intl.NumberFormat("ru-RU").format(Math.round(num));
}

/**
 * Форматирование валюты (сумы)
 */
export function formatCurrency(value?: number | null | undefined, currency: string = ""): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  const num = safeNumber(value);
  if (!Number.isFinite(num) || Number.isNaN(num)) {
    return "—";
  }
  return currency ? `${formatNumber(num)} ${currency}` : formatNumber(num);
}

/**
 * Форматирование процента
 */
export function formatPercent(value?: number | null | undefined, decimals: number = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  const num = safeNumber(value);
  if (!Number.isFinite(num) || Number.isNaN(num)) {
    return "—";
  }
  return `${num.toFixed(decimals)}%`;
}

/**
 * Форматирование количества с единицей измерения
 */
export function formatQuantity(value?: number | null | undefined, unit: string = "шт"): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  const num = safeNumber(value);
  if (!Number.isFinite(num) || Number.isNaN(num)) {
    return "—";
  }
  return `${formatNumber(num)} ${unit}`;
}

/**
 * Форматирование тренда (с + или -)
 */
export function formatTrend(value?: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  const num = safeNumber(value);
  if (!Number.isFinite(num) || Number.isNaN(num)) {
    return "—";
  }
  return `${num >= 0 ? "+" : ""}${num.toFixed(1)}%`;
}

/**
 * Форматирование в миллионах (для графиков)
 * 0 -> "0"
 * 1 000 000 -> "1.0 млн"
 * 12 500 000 -> "12.5 млн"
 */
export function formatMillions(value?: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "0";
  }
  const num = safeNumber(value);
  if (!Number.isFinite(num) || num === 0) {
    return "0";
  }
  const millions = num / 1000000;
  return `${millions.toFixed(1)} млн`;
}

/**
 * Форматирование денег без копеек (для среднего чека)
 * Округляет до целых чисел и форматирует с разделителями тысяч
 * 139195.5 -> "139 196"
 */
export function formatMoneyNoDecimals(value?: number | null | undefined, currency: string = ""): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  const avg = Number(value ?? 0);
  const avgRounded = Math.round(avg);
  if (!Number.isFinite(avgRounded) || Number.isNaN(avgRounded)) {
    return "—";
  }
  return currency ? `${avgRounded.toLocaleString("ru-RU")} ${currency}` : avgRounded.toLocaleString("ru-RU");
}
