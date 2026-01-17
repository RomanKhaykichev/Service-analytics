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
  if (value == null || value === undefined) {
    return "—";
  }
  const num = safeNumber(value);
  return new Intl.NumberFormat("ru-RU").format(Math.round(num));
}

/**
 * Форматирование валюты (сумы)
 */
export function formatCurrency(value?: number | null | undefined, currency: string = "сум"): string {
  if (value == null || value === undefined) {
    return "—";
  }
  const num = safeNumber(value);
  return `${formatNumber(num)} ${currency}`;
}

/**
 * Форматирование процента
 */
export function formatPercent(value?: number | null | undefined, decimals: number = 1): string {
  if (value == null || value === undefined) {
    return "—";
  }
  const num = safeNumber(value);
  return `${num.toFixed(decimals)}%`;
}

/**
 * Форматирование количества с единицей измерения
 */
export function formatQuantity(value?: number | null | undefined, unit: string = "шт"): string {
  if (value == null || value === undefined) {
    return "—";
  }
  const num = safeNumber(value);
  return `${formatNumber(num)} ${unit}`;
}

/**
 * Форматирование тренда (с + или -)
 */
export function formatTrend(value?: number | null | undefined): string {
  if (value == null || value === undefined) {
    return "—";
  }
  const num = safeNumber(value);
  return `${num >= 0 ? "+" : ""}${num.toFixed(1)}%`;
}
