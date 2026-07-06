import { format, startOfYear, subDays } from "date-fns";
import { apiGet, apiPost } from "@/lib/api";

export interface UzumSyncResult {
  ok: boolean;
  sync_id?: string;
  upload_batch_id?: string;
  imported?: Record<string, number>;
  warnings?: string[];
  store_limit_exceeded?: boolean;
  date_from?: string;
  date_to?: string;
}

export interface UzumSyncStatus {
  sync_id: string;
  status: "running" | "success" | "failed" | "skipped" | string;
  started_at?: string | null;
  finished_at?: string | null;
  error_message?: string | null;
  upload_batch_id?: string | null;
}

export const UZUM_SYNC_REQUEST_INTERRUPTED =
  "Не удалось завершить запрос. Если загрузка уже началась, она может продолжаться на сервере. Проверьте статус через несколько минут.";

const POLL_INTERVAL_MS = 7_000;
const MAX_POLL_MS = 15 * 60 * 1000;
const START_TIMEOUT_MS = 30_000;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function isNetworkError(err: unknown): boolean {
  if (err instanceof TypeError && err.message === "Failed to fetch") return true;
  if (err instanceof DOMException && err.name === "AbortError") return true;
  if (err instanceof Error && err.message.includes("Не удалось подключиться")) return true;
  if (err instanceof Error && err.message.includes("uvicorn")) return true;
  return false;
}

function isTrialPlan(plan?: string | null): boolean {
  const raw = (plan ?? "trial").trim().toLowerCase();
  return raw === "trial" || raw === "";
}

export function getSyncDateRange(plan?: string | null): { dateFrom: string; dateTo: string } {
  const now = new Date();
  const dateTo = format(now, "yyyy-MM-dd");
  if (isTrialPlan(plan)) {
    return { dateFrom: format(subDays(now, 59), "yyyy-MM-dd"), dateTo };
  }
  return { dateFrom: format(startOfYear(now), "yyyy-MM-dd"), dateTo };
}

/** @deprecated Use getSyncDateRange */
export function getYearToDateRange(): { dateFrom: string; dateTo: string } {
  return getSyncDateRange();
}

export async function startUzumSync(
  apiKey: string,
  plan?: string | null,
  acceptLanguage?: string | null,
): Promise<{ sync_id: string }> {
  const { dateFrom, dateTo } = getSyncDateRange(plan);
  return apiPost<{ ok: boolean; sync_id: string; status: string }>(
    "/api/uzum-seller/reports/sync/start",
    {
      api_key: apiKey.trim(),
      date_from: dateFrom,
      date_to: dateTo,
      ...(acceptLanguage ? { accept_language: acceptLanguage } : {}),
    },
    { timeoutMs: START_TIMEOUT_MS },
  );
}

export async function getUzumSyncStatus(syncId: string): Promise<UzumSyncStatus> {
  return apiGet<UzumSyncStatus>(`/api/uzum-seller/reports/sync/status/${syncId}`, undefined, {
    timeoutMs: 15_000,
  });
}

async function pollUzumSyncUntilDone(
  syncId: string,
  dateFrom: string,
  dateTo: string,
): Promise<UzumSyncResult> {
  const deadline = Date.now() + MAX_POLL_MS;

  while (Date.now() < deadline) {
    try {
      const status = await getUzumSyncStatus(syncId);

      if (status.status === "success") {
        return {
          ok: true,
          sync_id: syncId,
          upload_batch_id: status.upload_batch_id ?? undefined,
          date_from: dateFrom,
          date_to: dateTo,
        };
      }

      if (status.status === "failed" || status.status === "skipped") {
        throw new Error(status.error_message || "Sync failed");
      }
    } catch (err) {
      if (err instanceof Error && !isNetworkError(err)) {
        throw err;
      }
    }

    await sleep(POLL_INTERVAL_MS);
  }

  throw new Error(UZUM_SYNC_REQUEST_INTERRUPTED);
}

/** Start background sync and poll until success or failure. */
export async function syncUzumReportsToService(
  apiKey: string,
  plan?: string | null,
  acceptLanguage?: string | null,
): Promise<UzumSyncResult> {
  const { dateFrom, dateTo } = getSyncDateRange(plan);

  let syncId: string;
  try {
    const started = await startUzumSync(apiKey, plan, acceptLanguage);
    syncId = started.sync_id;
  } catch (err) {
    if (isNetworkError(err)) {
      throw new Error(UZUM_SYNC_REQUEST_INTERRUPTED);
    }
    throw err;
  }

  return pollUzumSyncUntilDone(syncId, dateFrom, dateTo);
}
