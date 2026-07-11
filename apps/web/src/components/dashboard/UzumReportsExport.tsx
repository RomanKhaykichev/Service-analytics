import { useCallback, useEffect, useMemo, useState } from "react";
import { format, subDays } from "date-fns";
import { useOptionalDateRange } from "@/contexts/DateRangeContext";
import { Download, Eye, FileSpreadsheet, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { apiGet, apiPost, apiPostDownload } from "@/lib/api";
import { useLanguage } from "@/contexts/LanguageContext";
import { cn } from "@/lib/utils";

interface ReportColumn {
  name: string;
  mapped: boolean;
}

interface ReportTemplate {
  id: string;
  sheet_name: string;
  file_name: string;
  hint: string;
  columns: ReportColumn[];
  needs_date_range: boolean;
}

interface PreviewResult {
  file_name: string;
  row_count: number;
  columns: ReportColumn[];
  rows: Record<string, unknown>[];
  warnings?: string[];
}

interface UzumReportsExportProps {
  apiKey: string;
  disabled?: boolean;
}

/** Uzum API export can take minutes for large catalogs (measured ~130s for left-out). */
const UZUM_REPORT_TIMEOUT_MS: Record<string, number> = {
  inventory_old: 210_000,
  sales: 120_000,
  expenses: 120_000,
  storage: 60_000,
};

function uzumReportTimeoutMs(reportId: string): number {
  return UZUM_REPORT_TIMEOUT_MS[reportId] ?? 60_000;
}

function formatApiError(err: unknown, fallback: string, rateLimitFallback?: string): string {
  if (!(err instanceof Error)) return fallback;
  const raw = err.message;
  try {
    const parsed = JSON.parse(raw) as { detail?: unknown };
    const detail = parsed.detail;
    if (typeof detail === "string") {
      if (detail.includes("429") && rateLimitFallback) return rateLimitFallback;
      return detail;
    }
  } catch {
    /* plain text from apiPost */
  }
  if (raw.includes("429") && rateLimitFallback) return rateLimitFallback;
  return raw || fallback;
}

export function UzumReportsExport({ apiKey, disabled }: UzumReportsExportProps) {
  const { t } = useLanguage();
  const dashboardRange = useOptionalDateRange();
  const dashboardFrom = dashboardRange?.dateFrom;
  const dashboardTo = dashboardRange?.dateTo;
  const [templates, setTemplates] = useState<ReportTemplate[]>([]);
  const [dateFrom, setDateFrom] = useState(() =>
    dashboardFrom || format(subDays(new Date(), 30), "yyyy-MM-dd")
  );
  const [dateTo, setDateTo] = useState(() => dashboardTo || format(new Date(), "yyyy-MM-dd"));

  useEffect(() => {
    if (!dashboardFrom && !dashboardTo) return;
    if (dashboardFrom) setDateFrom(dashboardFrom);
    if (dashboardTo) setDateTo(dashboardTo);
  }, [dashboardFrom, dashboardTo]);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [preview, setPreview] = useState<PreviewResult | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<{ reports: ReportTemplate[] }>("/api/uzum-seller/reports/templates")
      .then((data) => setTemplates(data.reports))
      .catch(() => setTemplates([]));
  }, []);

  const reportLabels = useMemo(
    () =>
      ({
        sales: t("report.salesReport"),
        expenses: t("report.expensesReport"),
        storage: t("report.storageReport"),
        inventory_old: t("report.inventoryOld"),
      }) as Record<string, string>,
    [t]
  );

  const runExport = useCallback(
    async (report: ReportTemplate) => {
      if (!apiKey.trim() || disabled) return;
      setLoadingId(report.id);
      setError(null);
      setWarnings([]);
      try {
        const exportWarnings = await apiPostDownload(
          "/api/uzum-seller/reports/export",
          {
            api_key: apiKey.trim(),
            report_type: report.id,
            date_from: report.needs_date_range ? dateFrom : undefined,
            date_to: report.needs_date_range ? dateTo : undefined,
          },
          report.file_name,
          { timeoutMs: uzumReportTimeoutMs(report.id) },
        );
        if (exportWarnings.length) {
          setWarnings(exportWarnings);
        }
      } catch (e) {
        setError(formatApiError(e, t("services.exportFailed"), t("services.rateLimit")));
      } finally {
        setLoadingId(null);
      }
    },
    [apiKey, dateFrom, dateTo, disabled, t]
  );

  const runPreview = useCallback(
    async (report: ReportTemplate) => {
      if (!apiKey.trim() || disabled) return;
      setPreviewId(report.id);
      setError(null);
      setWarnings([]);
      try {
        const result = await apiPost<PreviewResult>(
          "/api/uzum-seller/reports/preview",
          {
            api_key: apiKey.trim(),
            report_type: report.id,
            date_from: report.needs_date_range ? dateFrom : undefined,
            date_to: report.needs_date_range ? dateTo : undefined,
            preview_limit: 30,
          },
          { timeoutMs: uzumReportTimeoutMs(report.id) },
        );
        setPreview(result);
        setWarnings(result.warnings ?? []);
      } catch (e) {
        setError(formatApiError(e, t("services.previewFailed"), t("services.rateLimit")));
        setPreview(null);
        setWarnings([]);
      } finally {
        setPreviewId(null);
      }
    },
    [apiKey, dateFrom, dateTo, disabled, t]
  );

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <FileSpreadsheet className="h-5 w-5 text-primary" />
            {t("services.exportTitle")}
          </CardTitle>
          <CardDescription>{t("services.exportDescription")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-xs text-muted-foreground">{t("services.exportBoldHint")}</p>
          <div className="grid sm:grid-cols-2 gap-3 max-w-lg">
            <div className="space-y-1">
              <Label htmlFor="uzum-export-from">{t("filter.period")} — {t("services.dateFrom")}</Label>
              <Input
                id="uzum-export-from"
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                disabled={disabled}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="uzum-export-to">{t("services.dateTo")}</Label>
              <Input
                id="uzum-export-to"
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                disabled={disabled}
              />
            </div>
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {warnings.length > 0 && (
            <Alert>
              <AlertDescription>{warnings.join(" ")}</AlertDescription>
            </Alert>
          )}

          <div className="grid gap-3 md:grid-cols-2">
            {templates.map((report) => (
              <div
                key={report.id}
                className="rounded-lg border border-border p-4 space-y-3 bg-muted/20"
              >
                <div>
                  <p className="font-medium text-foreground">{reportLabels[report.id] ?? report.sheet_name}</p>
                  <p className="text-xs text-muted-foreground font-mono">{report.hint}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {report.columns.filter((c) => c.mapped).length}/{report.columns.length}{" "}
                    {t("services.columnsFromApi")}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant="default"
                    disabled={disabled || loadingId !== null || previewId !== null}
                    onClick={() => runExport(report)}
                  >
                    {loadingId === report.id ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-1" />
                    ) : (
                      <Download className="h-4 w-4 mr-1" />
                    )}
                    Excel
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={disabled || loadingId !== null || previewId !== null}
                    onClick={() => runPreview(report)}
                  >
                    {previewId === report.id ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-1" />
                    ) : (
                      <Eye className="h-4 w-4 mr-1" />
                    )}
                    {t("services.preview")}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {preview && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">{t("services.previewTitle")}</CardTitle>
            <CardDescription>
              {preview.file_name} · {preview.row_count} {t("services.rows")} · {t("services.previewShown")}{" "}
              {preview.rows.length}
            </CardDescription>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  {preview.columns.map((col) => (
                    <TableHead
                      key={col.name}
                      className={cn("whitespace-nowrap text-xs", !col.mapped && "font-bold")}
                    >
                      {col.name}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {preview.rows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={preview.columns.length} className="text-muted-foreground text-sm">
                      {t("services.noRows")}
                    </TableCell>
                  </TableRow>
                ) : (
                  preview.rows.map((row, idx) => (
                    <TableRow key={idx}>
                      {preview.columns.map((col) => (
                        <TableCell key={col.name} className="text-xs max-w-[200px] truncate">
                          {row[col.name] != null && row[col.name] !== "" ? String(row[col.name]) : "—"}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
