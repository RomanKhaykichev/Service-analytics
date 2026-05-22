/** Сдвиг ISO-даты (YYYY-MM-DD) на заданное число дней. */
export function addDaysISO(iso: string, days: number): string {
  const d = new Date(`${iso}T12:00:00`);
  d.setDate(d.getDate() + days);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** Последние 7 дней и предыдущие 7 дней относительно referenceDate (включительно). */
export function getWeeklyInsightRanges(referenceDate: string) {
  const lastWeekTo = referenceDate;
  const lastWeekFrom = addDaysISO(referenceDate, -6);
  const prevWeekTo = addDaysISO(lastWeekFrom, -1);
  const prevWeekFrom = addDaysISO(prevWeekTo, -6);
  return { lastWeekFrom, lastWeekTo, prevWeekFrom, prevWeekTo };
}
