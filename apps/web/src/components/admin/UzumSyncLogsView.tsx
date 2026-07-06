import { useCallback, useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";
import { useLanguage } from "@/contexts/LanguageContext";
import { cn } from "@/lib/utils";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { RefreshCw, FileSpreadsheet, Trash2 } from "lucide-react";
import { toast } from "sonner";

interface UzumSyncLogRow {
  id: string;
  user_id: string;
  user_email: string | null;
  started_at: string;
  finished_at: string | null;
  status: string;
  error_message: string | null;
  error_detail: string | null;
  upload_batch_id: string | null;
  trigger: string;
  last_api_sync_at: string | null;
}

interface UzumSyncLogsStats {
  active_count: number;
  days_count: number;
  success_count: number;
  failed_count: number;
  success_rate_percent: number | null;
  manual_count: number;
  scheduled_count: number;
}

interface UzumSyncLogsResponse {
  items: UzumSyncLogRow[];
  total_count: number;
  stats: UzumSyncLogsStats;
}

const PAGE_SIZE = 50;
const EXPORT_PAGE_SIZE = 500;
const TABLE_ERROR_MAX = 120;
const TABLE_SCROLL_MAX_ROWS = 10;
/** h-12 header + 10 data rows (3rem each) */
const TABLE_SCROLL_MAX_HEIGHT = "max-h-[33rem]";

function formatLogDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const day = String(d.getDate()).padStart(2, "0");
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const year = d.getFullYear();
  const hours = String(d.getHours()).padStart(2, "0");
  const minutes = String(d.getMinutes()).padStart(2, "0");
  return `${day}.${month}.${year} ${hours}:${minutes}`;
}

function formatSyncDuration(
  startedAt: string | null | undefined,
  finishedAt: string | null | undefined,
): string {
  if (!startedAt || !finishedAt) return "—";
  const start = new Date(startedAt);
  const end = new Date(finishedAt);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return "—";
  const ms = end.getTime() - start.getTime();
  if (ms < 0) return "—";

  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

/** UI label for uzum_sync_log.trigger (DB value unchanged). */
function formatSyncTrigger(trigger: string): string {
  if (trigger === "manual_incremental") return "manual";
  return trigger;
}

function statusClass(status: string): string {
  if (status === "success") return "text-green-700 dark:text-green-400";
  if (status === "failed") return "text-destructive";
  return "text-amber-700 dark:text-amber-400";
}

function errorSummaryText(row: UzumSyncLogRow): string | null {
  const text = row.error_message?.trim();
  if (!text) return null;
  if (text.length <= TABLE_ERROR_MAX) return text;
  return `${text.slice(0, TABLE_ERROR_MAX - 1)}…`;
}

function errorFullText(row: UzumSyncLogRow): string {
  return (row.error_detail || row.error_message || "").trim();
}

export function UzumSyncLogsView() {
  const { t } = useLanguage();
  const [items, setItems] = useState<UzumSyncLogRow[]>([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<UzumSyncLogsStats | null>(null);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailRow, setDetailRow] = useState<UzumSyncLogRow | null>(null);
  const [exporting, setExporting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const allOnPageSelected =
    items.length > 0 && items.every((row) => selectedIds.has(row.id));

  const toggleSelectAll = useCallback(() => {
    if (allOnPageSelected) {
      setSelectedIds(new Set());
      return;
    }
    setSelectedIds(new Set(items.map((row) => row.id)));
  }, [allOnPageSelected, items]);

  const toggleRowSelected = useCallback((id: string, checked: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  }, []);

  const fetchAllLogs = useCallback(async (): Promise<UzumSyncLogRow[]> => {
    const all: UzumSyncLogRow[] = [];
    let exportOffset = 0;
    while (true) {
      const data = await apiGet<UzumSyncLogsResponse>(
        `/api/admin/uzum-sync-logs?limit=${EXPORT_PAGE_SIZE}&offset=${exportOffset}`,
      );
      const batch = data.items ?? [];
      all.push(...batch);
      const totalCount = data.total_count ?? all.length;
      if (batch.length < EXPORT_PAGE_SIZE || all.length >= totalCount) break;
      exportOffset += EXPORT_PAGE_SIZE;
    }
    return all;
  }, []);

  const exportToExcel = useCallback(async () => {
    if (exporting) return;
    try {
      setExporting(true);
      const rows = await fetchAllLogs();
      if (rows.length === 0) {
        toast.error(t("admin.uzumSyncLogs.exportEmpty"));
        return;
      }
      const XLSX = await import("xlsx");
      const sheetRows = rows.map((row) => ({
        [t("admin.uzumSyncLogs.userId")]: row.user_id,
        [t("admin.uzumSyncLogs.email")]: row.user_email ?? "",
        [t("admin.uzumSyncLogs.startedAt")]: formatLogDateTime(row.started_at),
        [t("admin.uzumSyncLogs.finishedAt")]: formatLogDateTime(row.finished_at),
        [t("admin.uzumSyncLogs.duration")]: formatSyncDuration(row.started_at, row.finished_at),
        [t("admin.uzumSyncLogs.status")]: row.status,
        [t("admin.uzumSyncLogs.trigger")]: formatSyncTrigger(row.trigger),
        [t("admin.uzumSyncLogs.lastSync")]: formatLogDateTime(row.last_api_sync_at),
        [t("admin.uzumSyncLogs.error")]: row.error_message ?? "",
        [t("admin.uzumSyncLogs.errorDetailTitle")]: errorFullText(row),
        "upload_batch_id": row.upload_batch_id ?? "",
        id: row.id,
      }));
      const ws = XLSX.utils.json_to_sheet(sheetRows);
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, "Uzum sync");
      const now = new Date();
      const stamp = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
      XLSX.writeFile(wb, `uzum_sync_logs_${stamp}.xlsx`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : t("admin.uzumSyncLogs.exportFailed"));
    } finally {
      setExporting(false);
    }
  }, [exporting, fetchAllLogs, t]);

  const fetchLogs = useCallback(async () => {
    setError(null);
    setRefreshing(true);
    try {
      const data = await apiGet<UzumSyncLogsResponse>(
        `/api/admin/uzum-sync-logs?limit=${PAGE_SIZE}&offset=${offset}`,
      );
      setItems(data.items ?? []);
      setTotal(data.total_count ?? 0);
      setStats(data.stats ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRefreshing(false);
      setLoading(false);
    }
  }, [offset]);

  const deleteSelected = useCallback(async () => {
    if (deleting || selectedIds.size === 0) return;
    try {
      setDeleting(true);
      const res = await apiPost<{ ok: boolean; deleted: number }>(
        "/api/admin/uzum-sync-logs/delete",
        { ids: Array.from(selectedIds) },
      );
      toast.success(`${t("admin.uzumSyncLogs.deleteSuccess")}: ${res.deleted ?? 0}`);
      setSelectedIds(new Set());
      await fetchLogs();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : t("admin.uzumSyncLogs.deleteFailed"));
    } finally {
      setDeleting(false);
    }
  }, [deleting, selectedIds, fetchLogs, t]);

  useEffect(() => {
    setSelectedIds(new Set());
  }, [offset]);

  useEffect(() => {
    void fetchLogs();
  }, [fetchLogs]);

  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-4">
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3">
          <div className="rounded-lg border border-border bg-card px-4 py-3">
            <p className="text-xs text-muted-foreground">{t("admin.uzumSyncLogs.metricActive")}</p>
            <p className="text-xl font-semibold text-primary">{stats.active_count}</p>
          </div>
          <div className="rounded-lg border border-border bg-card px-4 py-3">
            <p className="text-xs text-muted-foreground">{t("admin.uzumSyncLogs.metricDays")}</p>
            <p className="text-xl font-semibold text-foreground">{stats.days_count}</p>
          </div>
          <div className="rounded-lg border border-border bg-card px-4 py-3">
            <p className="text-xs text-muted-foreground">{t("admin.uzumSyncLogs.metricSuccess")}</p>
            <p className="text-xl font-semibold text-green-700 dark:text-green-400">{stats.success_count}</p>
          </div>
          <div className="rounded-lg border border-border bg-card px-4 py-3">
            <p className="text-xs text-muted-foreground">{t("admin.uzumSyncLogs.metricFailed")}</p>
            <p className="text-xl font-semibold text-destructive">{stats.failed_count}</p>
          </div>
          <div className="rounded-lg border border-border bg-card px-4 py-3">
            <p className="text-xs text-muted-foreground">{t("admin.uzumSyncLogs.metricSuccessRate")}</p>
            <p className="text-xl font-semibold text-foreground">
              {stats.success_rate_percent != null ? `${stats.success_rate_percent}%` : "—"}
            </p>
          </div>
          <div className="rounded-lg border border-border bg-card px-4 py-3">
            <p className="text-xs text-muted-foreground">{t("admin.uzumSyncLogs.metricManual")}</p>
            <p className="text-xl font-semibold text-foreground">{stats.manual_count}</p>
          </div>
          <div className="rounded-lg border border-border bg-card px-4 py-3">
            <p className="text-xs text-muted-foreground">{t("admin.uzumSyncLogs.metricScheduled")}</p>
            <p className="text-xl font-semibold text-foreground">{stats.scheduled_count}</p>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-foreground">{t("admin.uzumSyncLogs.title")}</h2>
          <p className="text-sm text-muted-foreground">{t("admin.uzumSyncLogs.subtitle")}</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={toggleSelectAll}
            disabled={loading || items.length === 0}
          >
            {allOnPageSelected ? t("admin.uzumSyncLogs.deselectAll") : t("admin.uzumSyncLogs.selectAll")}
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => void deleteSelected()}
            disabled={deleting || refreshing || selectedIds.size === 0}
          >
            <Trash2 className={cn("h-4 w-4", deleting && "opacity-50")} />
            {deleting ? t("admin.uzumSyncLogs.deleting") : t("admin.uzumSyncLogs.deleteSelected")}
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => void exportToExcel()}
            disabled={exporting || refreshing}
          >
            <FileSpreadsheet className={cn("h-4 w-4", exporting && "opacity-50")} />
            {exporting ? t("admin.uzumSyncLogs.exporting") : t("admin.uzumSyncLogs.exportExcel")}
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={() => void fetchLogs()} disabled={refreshing}>
            <RefreshCw className={cn("h-4 w-4", refreshing && "animate-spin")} />
            {t("admin.uzumSyncLogs.refresh")}
          </Button>
        </div>
      </div>

      {error && (
        <p className="text-sm text-destructive">{error}</p>
      )}

      <div
        className={cn(
          "rounded-lg border border-border overflow-x-auto",
          items.length > TABLE_SCROLL_MAX_ROWS && cn(TABLE_SCROLL_MAX_HEIGHT, "overflow-y-auto"),
        )}
      >
        <Table wrapperClassName={items.length > TABLE_SCROLL_MAX_ROWS ? "overflow-visible" : undefined}>
          <TableHeader className="sticky top-0 z-10 bg-background [&_th]:bg-background">
            <TableRow className="bg-background hover:bg-background">
              <TableHead className="w-12 text-center sticky left-0 z-20 bg-background">
                <span className="sr-only">{t("admin.uzumSyncLogs.selectRow")}</span>
              </TableHead>
              <TableHead>{t("admin.uzumSyncLogs.userId")}</TableHead>
              <TableHead>{t("admin.uzumSyncLogs.email")}</TableHead>
              <TableHead>{t("admin.uzumSyncLogs.startedAt")}</TableHead>
              <TableHead>{t("admin.uzumSyncLogs.finishedAt")}</TableHead>
              <TableHead>{t("admin.uzumSyncLogs.duration")}</TableHead>
              <TableHead>{t("admin.uzumSyncLogs.status")}</TableHead>
              <TableHead>{t("admin.uzumSyncLogs.trigger")}</TableHead>
              <TableHead>{t("admin.uzumSyncLogs.lastSync")}</TableHead>
              <TableHead className="min-w-[180px]">{t("admin.uzumSyncLogs.error")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading && items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={10} className="text-center text-muted-foreground py-8">
                  {t("admin.uzumSyncLogs.loading")}
                </TableCell>
              </TableRow>
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={10} className="text-center text-muted-foreground py-8">
                  {t("admin.uzumSyncLogs.empty")}
                </TableCell>
              </TableRow>
            ) : (
              items.map((row) => {
                const summary = errorSummaryText(row);
                const hasDetail = !!errorFullText(row);
                return (
                  <TableRow key={row.id} data-state={selectedIds.has(row.id) ? "selected" : undefined}>
                    <TableCell className="w-12 text-center sticky left-0 z-10 bg-background">
                      <Checkbox
                        checked={selectedIds.has(row.id)}
                        onCheckedChange={(checked) => toggleRowSelected(row.id, checked === true)}
                        aria-label={t("admin.uzumSyncLogs.selectRow")}
                      />
                    </TableCell>
                    <TableCell className="font-mono text-xs">{row.user_id}</TableCell>
                    <TableCell className="text-sm">{row.user_email ?? "—"}</TableCell>
                    <TableCell className="text-sm whitespace-nowrap">{formatLogDateTime(row.started_at)}</TableCell>
                    <TableCell className="text-sm whitespace-nowrap">{formatLogDateTime(row.finished_at)}</TableCell>
                    <TableCell className="text-sm whitespace-nowrap font-mono tabular-nums">
                      {formatSyncDuration(row.started_at, row.finished_at)}
                    </TableCell>
                    <TableCell className={cn("text-sm font-medium capitalize", statusClass(row.status))}>
                      {row.status}
                    </TableCell>
                    <TableCell className="text-sm">{formatSyncTrigger(row.trigger)}</TableCell>
                    <TableCell className="text-sm whitespace-nowrap">{formatLogDateTime(row.last_api_sync_at)}</TableCell>
                    <TableCell className="text-xs text-muted-foreground max-w-[220px]">
                      {summary ? (
                        <button
                          type="button"
                          className={cn(
                            "text-left break-words",
                            hasDetail && "underline underline-offset-2 hover:text-foreground",
                          )}
                          onClick={() => hasDetail && setDetailRow(row)}
                          disabled={!hasDetail}
                        >
                          {summary}
                        </button>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>

      <Dialog open={!!detailRow} onOpenChange={(open) => !open && setDetailRow(null)}>
        <DialogContent className="max-w-3xl max-h-[85vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>{t("admin.uzumSyncLogs.errorDetailTitle")}</DialogTitle>
          </DialogHeader>
          {detailRow && (
            <div className="space-y-2 min-h-0 flex-1 overflow-hidden flex flex-col">
              <p className="text-sm text-muted-foreground">
                {detailRow.user_email ?? detailRow.user_id} · {formatLogDateTime(detailRow.started_at)}
              </p>
              <pre className="flex-1 overflow-auto rounded-md border border-border bg-muted/40 p-4 text-sm leading-relaxed whitespace-pre-wrap break-words font-mono">
                {errorFullText(detailRow)}
              </pre>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>
            {t("admin.uzumSyncLogs.page")} {page} / {totalPages} ({total})
          </span>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={offset <= 0 || refreshing}
              onClick={() => setOffset((v) => Math.max(0, v - PAGE_SIZE))}
            >
              {t("admin.uzumSyncLogs.prev")}
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={offset + PAGE_SIZE >= total || refreshing}
              onClick={() => setOffset((v) => v + PAGE_SIZE)}
            >
              {t("admin.uzumSyncLogs.next")}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
