/**
 * Default period: last 30 days (to = today, from = today - 30 days).
 * Returns YYYY-MM-DD strings.
 */
export function getDefaultDateRange(): { dateFrom: string; dateTo: string } {
  const to = new Date();
  const from = new Date();
  from.setDate(from.getDate() - 30);
  return {
    dateFrom: from.toISOString().slice(0, 10),
    dateTo: to.toISOString().slice(0, 10),
  };
}

/**
 * Default range within bounds: to = maxDate, from = max(maxDate - 30 days, minDate).
 * minDate/maxDate must be YYYY-MM-DD; returns YYYY-MM-DD.
 */
export function getDefaultDateRangeInBounds(
  minDate: string,
  maxDate: string
): { dateFrom: string; dateTo: string } {
  const to = maxDate;
  const maxD = new Date(maxDate);
  const fromD = new Date(maxD);
  fromD.setDate(fromD.getDate() - 30);
  const fromStr = fromD.toISOString().slice(0, 10);
  const from = fromStr < minDate ? minDate : fromStr;
  return { dateFrom: from, dateTo: to };
}

/** Both required and from <= to. */
export function isValidRange(dateFrom: string, dateTo: string): boolean {
  if (!dateFrom || !dateTo) return false;
  const from = new Date(dateFrom);
  const to = new Date(dateTo);
  if (isNaN(from.getTime()) || isNaN(to.getTime())) return false;
  return from <= to;
}

/**
 * Clamp date range to [minDate, maxDate].
 * from = max(from, minDate), to = min(to, maxDate). Ensures from <= to.
 * Returns { dateFrom, dateTo } in YYYY-MM-DD.
 */
export function clampRange(
  dateFrom: string,
  dateTo: string,
  minDate: string,
  maxDate: string
): { dateFrom: string; dateTo: string } {
  let from = dateFrom;
  let to = dateTo;
  if (from < minDate) from = minDate;
  if (from > maxDate) from = maxDate;
  if (to < minDate) to = minDate;
  if (to > maxDate) to = maxDate;
  if (from > to) to = from;
  return { dateFrom: from, dateTo: to };
}
