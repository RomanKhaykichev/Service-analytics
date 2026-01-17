/**
 * Форматирование числа с разделителями тысяч
 */
export function formatNumber(value: number): string {
  return new Intl.NumberFormat("ru-RU").format(Math.round(value));
}

/**
 * Форматирование валюты (сумы)
 */
export function formatCurrency(value: number, currency: string = "сум"): string {
  return `${formatNumber(value)} ${currency}`;
}

/**
 * Форматирование процента
 */
export function formatPercent(value: number, decimals: number = 1): string {
  return `${value.toFixed(decimals)}%`;
}

/**
 * Форматирование количества с единицей измерения
 */
export function formatQuantity(value: number, unit: string = "шт"): string {
  return `${formatNumber(value)} ${unit}`;
}

/**
 * Форматирование тренда (с + или -)
 */
export function formatTrend(value: number): string {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}
