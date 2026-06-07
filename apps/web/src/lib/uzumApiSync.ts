import { format, startOfYear } from "date-fns";
import { apiPost } from "@/lib/api";

export interface UzumSyncResult {
  ok: boolean;
  upload_batch_id?: string;
  imported?: Record<string, number>;
  warnings?: string[];
  store_limit_exceeded?: boolean;
  date_from?: string;
  date_to?: string;
}

export function getYearToDateRange(): { dateFrom: string; dateTo: string } {
  const now = new Date();
  return {
    dateFrom: format(startOfYear(now), "yyyy-MM-dd"),
    dateTo: format(now, "yyyy-MM-dd"),
  };
}

export async function syncUzumReportsToService(apiKey: string): Promise<UzumSyncResult> {
  const { dateFrom, dateTo } = getYearToDateRange();
  return apiPost<UzumSyncResult>(
    "/api/uzum-seller/reports/sync",
    {
      api_key: apiKey.trim(),
      date_from: dateFrom,
      date_to: dateTo,
    },
    { timeoutMs: 600_000 },
  );
}
